/* List of environment variables required for Playwright tests */
export const requiredSupabaseCreds = [
  'SUPABASE_URL',
  'SUPABASE_SERVICE_ROLE_KEY',
];

export const missingSupabaseCreds = requiredSupabaseCreds.some(
  (name) => !process.env[name],
);
