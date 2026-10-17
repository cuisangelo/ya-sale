"use client";

import { useEffect, useState } from "react";
import styles from "../../app/landing.module.css";

// The trailing slash matters: the server answers MCP on /mcp/ and rejects a POST to /mcp.
const MCP_PATH = "/mcp/";

export function McpUrl() {
  const [url, setUrl] = useState(MCP_PATH);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setUrl(new URL(MCP_PATH, window.location.origin).href);
  }, []);

  async function copy() {
    await navigator.clipboard.writeText(url);
    setCopied(true);
  }

  return (
    <div className={styles.mcpUrl}>
      <code>{url}</code>
      <button type="button" className="btn btn-secondary" onClick={copy}>
        {copied ? "Copiada" : "Copiar"}
      </button>
    </div>
  );
}
