const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

export function validateEmail(value: string): string | undefined {
  const email = value.trim()
  if (!email) return 'Enter your email address.'
  if (!EMAIL_PATTERN.test(email)) return 'Enter an email address in the format name@company.com.'
  return undefined
}

export function validateRequired(value: string, label: string): string | undefined {
  return value.trim() ? undefined : `Enter your ${label}.`
}

export interface PasswordCheck {
  id: string
  label: string
  met: boolean
}

export function passwordChecks(password: string): PasswordCheck[] {
  return [
    { id: 'length', label: 'At least 10 characters', met: password.length >= 10 },
    { id: 'case', label: 'Upper- and lowercase letters', met: /[a-z]/.test(password) && /[A-Z]/.test(password) },
    { id: 'number', label: 'At least one number', met: /\d/.test(password) },
    { id: 'symbol', label: 'At least one symbol, like ! or #', met: /[^A-Za-z0-9]/.test(password) },
  ]
}

export type PasswordStrength = 'empty' | 'weak' | 'fair' | 'strong'

export function passwordStrength(password: string): PasswordStrength {
  if (!password) return 'empty'
  const met = passwordChecks(password).filter((check) => check.met).length
  if (met <= 2) return 'weak'
  if (met === 3) return 'fair'
  return 'strong'
}

export function validateNewPassword(password: string): string | undefined {
  if (!password) return 'Create a password.'
  if (password.length < 10) return 'Use at least 10 characters.'
  if (passwordStrength(password) === 'weak') return 'Make your password stronger — add a number, symbol, or mixed-case letters.'
  return undefined
}

export function validateConfirmPassword(password: string, confirm: string): string | undefined {
  if (!confirm) return 'Re-enter your password.'
  if (password !== confirm) return "These passwords don't match."
  return undefined
}
