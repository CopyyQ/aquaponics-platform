import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { AppProviders } from "@/app/providers/app-providers"
import { AppRouter } from "@/app/router/canonical-router"
import "@/index.css"

createRoot(document.getElementById("root")!).render(<StrictMode><AppProviders><AppRouter /></AppProviders></StrictMode>)
