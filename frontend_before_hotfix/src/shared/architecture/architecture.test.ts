import { readFileSync, readdirSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

const sourceRoot = join(process.cwd(), "src")
function filesAt(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    return entry.isDirectory() ? filesAt(path) : /\.(ts|tsx)$/.test(entry.name) ? [path] : []
  })
}
function imports(file: string) {
  return [...readFileSync(file, "utf8").matchAll(/from\s+["'](@\/[^"']+)["']/g)].map((match) => match[1])
}

describe("frontend dependency boundaries", () => {
  it("does not allow reverse layer imports", () => {
    const rules: Array<[string, string[]]> = [["shared", ["app", "pages", "widgets", "features", "entities"]], ["entities", ["app", "pages", "widgets", "features"]], ["features", ["app", "pages", "widgets"]], ["widgets", ["app", "pages"]]]
    for (const file of filesAt(sourceRoot)) {
      const layer = relative(sourceRoot, file).split("/")[0]
      const forbidden = rules.find(([name]) => name === layer)?.[1] ?? []
      for (const imported of imports(file)) expect(forbidden.some((name) => imported.startsWith(`@/${name}/`))).toBe(false)
    }
  })
})
