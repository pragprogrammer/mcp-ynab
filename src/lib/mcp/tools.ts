import { tool, type CoreTool } from "ai";
import { z } from "zod";
import { getMcpClient } from "./client";

type JsonSchemaProperty = {
  type?: string;
  description?: string;
  enum?: string[];
  default?: unknown;
};

type JsonSchema = {
  type?: string;
  properties?: Record<string, JsonSchemaProperty>;
  required?: string[];
};

function jsonSchemaPropertyToZod(
  prop: JsonSchemaProperty,
  required: boolean
): z.ZodTypeAny {
  let schema: z.ZodTypeAny;

  switch (prop.type) {
    case "number":
    case "integer":
      schema = z.number();
      break;
    case "boolean":
      schema = z.boolean();
      break;
    case "string":
    default:
      if (prop.enum) {
        schema = z.enum(prop.enum as [string, ...string[]]);
      } else {
        schema = z.string();
      }
      break;
  }

  if (prop.description) {
    schema = schema.describe(prop.description);
  }

  if (!required) {
    schema = schema.optional();
  }

  return schema;
}

function jsonSchemaToZod(schema: JsonSchema): z.ZodObject<z.ZodRawShape> {
  const shape: z.ZodRawShape = {};
  const properties = schema.properties ?? {};
  const required = new Set(schema.required ?? []);

  for (const [key, prop] of Object.entries(properties)) {
    shape[key] = jsonSchemaPropertyToZod(prop, required.has(key));
  }

  return z.object(shape);
}

export async function getMcpTools(): Promise<Record<string, CoreTool>> {
  const client = await getMcpClient();
  const { tools: mcpTools } = await client.listTools();
  const aiTools: Record<string, CoreTool> = {};

  for (const mcpTool of mcpTools) {
    const zodSchema = jsonSchemaToZod(mcpTool.inputSchema as JsonSchema);

    aiTools[mcpTool.name] = tool({
      description: mcpTool.description ?? mcpTool.name,
      inputSchema: zodSchema,
      execute: async (args) => {
        const result = await client.callTool({
          name: mcpTool.name,
          arguments: args as Record<string, unknown>,
        });
        const textContent = result.content as Array<{
          type: string;
          text?: string;
        }>;
        return (
          textContent.find((c) => c.type === "text")?.text ??
          JSON.stringify(result.content)
        );
      },
    });
  }

  return aiTools;
}
