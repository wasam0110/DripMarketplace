// Audit-only syntax index. It never imports or executes application code.
const fs = require('node:fs');
const path = require('node:path');
const ts = require('../drip-frontend/node_modules/typescript');
const root = path.resolve(__dirname, '..');
const paths = JSON.parse(fs.readFileSync(0, 'utf8'));
const output = {};
for (const rel of paths) {
  const source = fs.readFileSync(path.join(root, rel), 'utf8');
  const sf = ts.createSourceFile(rel, source, ts.ScriptTarget.Latest, true);
  const symbols = [], imports = [], hooks = new Set(), requests = [];
  const line = n => sf.getLineAndCharacterOfPosition(n).line + 1;
  function values(node) {
    if (!node) return ['{dynamic}'];
    if (ts.isStringLiteralLike(node)) return [node.text];
    if (ts.isParenthesizedExpression(node)) return values(node.expression);
    if (ts.isConditionalExpression(node)) return [...values(node.whenTrue), ...values(node.whenFalse)];
    if (ts.isTemplateExpression(node)) {
      let out = [node.head.text];
      for (const span of node.templateSpans) out = out.flatMap(head => values(span.expression).map(value => head + value + span.literal.text));
      return out.slice(0, 64);
    }
    if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.PlusToken) return values(node.left).flatMap(a => values(node.right).map(b => a + b)).slice(0, 64);
    return ['{dynamic}'];
  }
  function visit(node, owner = '') {
    if (ts.isImportDeclaration(node)) imports.push(node.moduleSpecifier.text);
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && /^use[A-Z]/.test(node.expression.text)) hooks.add(node.expression.text);
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && ['request', 'useOrderRead', 'useResource'].includes(node.expression.text)) {
      const options = node.arguments[1];
      let method = 'GET';
      if (node.expression.text === 'request' && options) {
        method = ts.isObjectLiteralExpression(options) ? 'GET' : '?';
        if (ts.isObjectLiteralExpression(options)) for (const property of options.properties) {
          if (ts.isSpreadAssignment(property)) method = '?';
          if (property.name?.getText(sf).replace(/['"]/g, '') === 'method') method = ts.isPropertyAssignment(property) && ts.isStringLiteralLike(property.initializer) ? property.initializer.text : '?';
        }
      }
      requests.push({line: line(node.getStart(sf)), helper: node.expression.text, method, paths: values(node.arguments[0])});
    }
    let name;
    if (ts.isFunctionDeclaration(node) || ts.isClassDeclaration(node) || ts.isInterfaceDeclaration(node) || ts.isTypeAliasDeclaration(node) || ts.isMethodDeclaration(node)) name = node.name?.getText(sf);
    if (ts.isVariableDeclaration(node) && node.initializer && (ts.isArrowFunction(node.initializer) || ts.isFunctionExpression(node.initializer))) name = node.name.getText(sf);
    if (name) symbols.push({name: owner ? `${owner}.${name}` : name, kind: ts.SyntaxKind[node.kind], start: line(node.getStart(sf)), end: line(node.end), doc: '', calls: []});
    ts.forEachChild(node, child => visit(child, name || owner));
  }
  visit(sf);
  output[rel] = {symbols, imports: [...new Set(imports)], hooks: [...hooks], requests, parse_errors: sf.parseDiagnostics.map(d => ts.flattenDiagnosticMessageText(d.messageText, ' '))};
}
process.stdout.write(JSON.stringify(output));
