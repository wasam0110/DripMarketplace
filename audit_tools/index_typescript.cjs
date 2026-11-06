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
  const symbols = [], imports = [], hooks = new Set();
  const line = n => sf.getLineAndCharacterOfPosition(n).line + 1;
  function visit(node, owner = '') {
    if (ts.isImportDeclaration(node)) imports.push(node.moduleSpecifier.text);
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && /^use[A-Z]/.test(node.expression.text)) hooks.add(node.expression.text);
    let name;
    if (ts.isFunctionDeclaration(node) || ts.isClassDeclaration(node) || ts.isInterfaceDeclaration(node) || ts.isTypeAliasDeclaration(node) || ts.isMethodDeclaration(node)) name = node.name?.getText(sf);
    if (ts.isVariableDeclaration(node) && node.initializer && (ts.isArrowFunction(node.initializer) || ts.isFunctionExpression(node.initializer))) name = node.name.getText(sf);
    if (name) symbols.push({name: owner ? `${owner}.${name}` : name, kind: ts.SyntaxKind[node.kind], start: line(node.getStart(sf)), end: line(node.end), doc: '', calls: []});
    ts.forEachChild(node, child => visit(child, name || owner));
  }
  visit(sf);
  output[rel] = {symbols, imports: [...new Set(imports)], hooks: [...hooks], parse_errors: sf.parseDiagnostics.map(d => ts.flattenDiagnosticMessageText(d.messageText, ' '))};
}
process.stdout.write(JSON.stringify(output));
