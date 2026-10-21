const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const solc = require("solc");

const projectRoot = path.resolve(__dirname, "..");
const sourcePath = path.join(projectRoot, "src", "LedgerAnchorRegistry.sol");
const artifactPath = path.join(projectRoot, "artifacts", "LedgerAnchorRegistry.json");
const source = fs.readFileSync(sourcePath, "utf8");
const input = {
  language: "Solidity",
  sources: { "LedgerAnchorRegistry.sol": { content: source } },
  settings: {
    optimizer: { enabled: true, runs: 200 },
    evmVersion: "cancun",
    metadata: { bytecodeHash: "none" },
    outputSelection: {
      "*": { "*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"] },
    },
  },
};

function resolveImport(importPath) {
  try {
    return { contents: fs.readFileSync(require.resolve(importPath, { paths: [projectRoot] }), "utf8") };
  } catch {
    return { error: `Unable to resolve contract import: ${importPath}` };
  }
}

const output = JSON.parse(solc.compile(JSON.stringify(input), { import: resolveImport }));
const errors = (output.errors ?? []).filter((entry) => entry.severity === "error");
for (const entry of output.errors ?? []) {
  if (entry.severity === "error") process.stderr.write(`${entry.formattedMessage}\n`);
}
if (errors.length > 0) process.exit(1);

const compiled = output.contracts["LedgerAnchorRegistry.sol"].LedgerAnchorRegistry;
const artifact = {
  contractName: "LedgerAnchorRegistry",
  contractVersion: "1.0.0",
  compilerVersion: solc.version(),
  sourceHash: createHash("sha256").update(source).digest("hex"),
  abi: compiled.abi,
  bytecode: `0x${compiled.evm.bytecode.object}`,
  deployedBytecode: `0x${compiled.evm.deployedBytecode.object}`,
};
fs.mkdirSync(path.dirname(artifactPath), { recursive: true });
fs.writeFileSync(artifactPath, `${JSON.stringify(artifact, null, 2)}\n`);
process.stdout.write(`Compiled ${artifact.contractName} with ${artifact.compilerVersion}\n`);
