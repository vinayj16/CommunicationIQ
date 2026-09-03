module.exports = {
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  extends: [
    "next/core-web-vitals",
    "plugin:@typescript-eslint/recommended",
  ],
  ignorePatterns: ["app/proctoring/**/*.js", "app/proctoring/**/*.jsx", "app/utils/**/*.js"],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    project: "./tsconfig.json",
  },
  plugins: ["@typescript-eslint", "@next/next"],
  rules: {
    "@next/next/no-html-link-for-pages": "off",
    "@next/next/no-img-element": "off",
    "@typescript-eslint/no-unused-vars": "off",
    "@typescript-eslint/no-explicit-any": "off",
    "react/no-unescaped-entities": "off",
    "prefer-const": "off",
    "react-hooks/rules-of-hooks": "off",
    "react-hooks/exhaustive-deps": "warn",
  },
  settings: {
    next: {
      rootDir: ".",
    },
  },
};