export interface PasswordChange { current_password: string; new_password: string; confirm_password: string }
export function validatePasswordChange(value: PasswordChange): void {
  if (!value.current_password) throw new Error('Enter your current password.')
  const length = [...value.new_password].length
  if (length < 8 || length > 128 || !/[A-Z]/.test(value.new_password) || !/[a-z]/.test(value.new_password) || !/[0-9]/.test(value.new_password)) {
    throw new Error('Use 8–128 characters with at least one uppercase letter, one lowercase letter and one number.')
  }
  if (value.new_password !== value.confirm_password) throw new Error('New password and confirmation do not match.')
}
