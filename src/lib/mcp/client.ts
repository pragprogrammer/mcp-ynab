import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import path from "path";

const REPO_ROOT = process.cwd();

interface McpClientState {
  client: Client;
  transport: StdioClientTransport;
}

const globalForMcp = globalThis as unknown as {
  __mcpClient?: McpClientState;
  __mcpInitPromise?: Promise<McpClientState>;
};

async function createClient(): Promise<McpClientState> {
  const transport = new StdioClientTransport({
    command: "uv",
    args: ["run", "python", "-m", "server.server"],
    cwd: REPO_ROOT,
    env: {
      ...process.env,
      YNAB_API_KEY: process.env.YNAB_API_KEY ?? "",
    },
    stderr: "pipe",
  });

  transport.stderr?.on("data", (chunk: Buffer) => {
    console.error("[MCP Server]", chunk.toString());
  });

  const client = new Client(
    { name: "ynab-chat", version: "0.1.0" },
    { capabilities: {} }
  );

  await client.connect(transport);
  return { client, transport };
}

export async function getMcpClient(): Promise<Client> {
  if (globalForMcp.__mcpClient) {
    try {
      // Verify connection is alive by listing tools
      await globalForMcp.__mcpClient.client.listTools();
      return globalForMcp.__mcpClient.client;
    } catch {
      // Connection dead, recreate
      globalForMcp.__mcpClient = undefined;
      globalForMcp.__mcpInitPromise = undefined;
    }
  }

  if (!globalForMcp.__mcpInitPromise) {
    globalForMcp.__mcpInitPromise = createClient()
      .then((state) => {
        globalForMcp.__mcpClient = state;
        return state;
      })
      .catch((err) => {
        globalForMcp.__mcpInitPromise = undefined;
        throw err;
      });
  }

  const state = await globalForMcp.__mcpInitPromise;
  return state.client;
}
