import { rm } from "node:fs/promises";
import { resolve } from "node:path";

await rm(resolve("www/assets"), { recursive: true, force: true });
