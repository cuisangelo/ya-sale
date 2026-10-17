"use client";

import { useEffect, useState } from "react";
import styles from "../../app/landing.module.css";

// /mcp/ is where the MCP app is mounted, so it works on every deployed backend version.
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
