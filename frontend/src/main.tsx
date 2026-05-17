import React from "react";
import { createRoot } from "react-dom/client";
import { ConfigProvider } from "antd";
import "antd/dist/reset.css";
import "./styles.css";
import { App } from "./App";

const root = document.getElementById("root");

if (root) {
  createRoot(root).render(
    <React.StrictMode>
      <ConfigProvider autoInsertSpaceInButton={false}>
        <App />
      </ConfigProvider>
    </React.StrictMode>
  );
}
