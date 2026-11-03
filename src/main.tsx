import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import AIMZDashboard from "./AIMZDashboard";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AIMZDashboard />
  </StrictMode>
);
