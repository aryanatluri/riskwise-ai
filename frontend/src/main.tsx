import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { SessionProvider, isAdmin, useSession } from "./lib/session";
import { Audit } from "./pages/Audit";
import { ContractDetail } from "./pages/ContractDetail";
import { Contracts } from "./pages/Contracts";
import { CreateOrg } from "./pages/CreateOrg";
import { Policies } from "./pages/Policies";
import { Review } from "./pages/Review";
import { Settings } from "./pages/Settings";
import { SignIn } from "./pages/SignIn";
import "./styles.css";

function App() {
  const { ready, signedIn, org } = useSession();
  if (!ready) return null;
  if (!signedIn) return <SignIn />;
  if (!org) return <CreateOrg />;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/review" replace />} />
        <Route path="review" element={<Review />} />
        <Route path="contracts" element={<Contracts />} />
        <Route path="contracts/:id" element={<ContractDetail />} />
        <Route path="policies" element={<Policies />} />
        {isAdmin(org) && <Route path="settings" element={<Settings />} />}
        {isAdmin(org) && <Route path="audit" element={<Audit />} />}
        <Route path="*" element={<Navigate to="/review" replace />} />
      </Route>
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <SessionProvider>
        <App />
      </SessionProvider>
    </BrowserRouter>
  </StrictMode>,
);
