import js from "@eslint/js"
import reactHooks from "eslint-plugin-react-hooks"
import tseslint from "typescript-eslint"

export default tseslint.config(
  { ignores: ["dist", "playwright-report", "test-results", "blob-report", "playwright/.auth"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
  {
    files: ["src/shared/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", { "patterns": ["@/app/**", "@/pages/**", "@/widgets/**", "@/features/**", "@/entities/**"] }],
    },
  },
  {
    files: ["src/entities/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", { "patterns": ["@/app/**", "@/pages/**", "@/widgets/**", "@/features/**"] }],
    },
  },
  {
    files: ["src/features/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", { "patterns": ["@/app/**", "@/pages/**", "@/widgets/**"] }],
    },
  },
  {
    files: ["src/widgets/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", { "patterns": ["@/app/**", "@/pages/**"] }],
    },
  },
)
