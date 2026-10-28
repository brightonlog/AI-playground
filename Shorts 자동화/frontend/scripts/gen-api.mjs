// Regenerate src/api/schema.d.ts from the FastAPI app (no running server needed).
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const spec = execFileSync("uv", ["run", "python", "-m", "app.openapi_dump"], {
  cwd: join(root, "..", "backend"),
  encoding: "utf-8",
});
// Pass the parsed object, not a file path: the parser mangles non-ASCII paths.
const ast = await openapiTS(JSON.parse(spec));
writeFileSync(join(root, "src", "api", "schema.d.ts"), astToString(ast));
console.log("src/api/schema.d.ts updated");
