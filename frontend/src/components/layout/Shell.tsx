import { Link, useLocation } from "react-router-dom";
import { BRAND } from "@/config";
import { motion } from "framer-motion";
import logo from "@/assets/slenth-logo.png";

const Shell = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  
  const tabs = [
    { name: "Dashboard", path: "/" },
    { name: "Upload", path: "/upload" },
    { name: "Rules", path: "/rules" },
  ];

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <header className="flex-shrink-0 border-b border-border bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4">
          <div className="flex h-16 items-center justify-between">
            {/* Logo & Brand */}
            <Link to="/" className="flex items-center gap-3 group">
              <div className="h-10 w-10 rounded-lg flex items-center justify-center overflow-hidden">
                <img src={logo} alt={BRAND.name} className="h-full w-full object-contain" />
              </div>
              <span className="text-xl font-bold text-foreground">{BRAND.name}</span>
            </Link>

            {/* Navigation Tabs */}
            <nav className="flex gap-1">
              {tabs.map((tab) => {
                const isActive = location.pathname === tab.path;
                return (
                  <Link
                    key={tab.path}
                    to={tab.path}
                    className="relative px-4 py-2 text-sm font-medium rounded-lg transition-colors"
                  >
                    <span
                      className={
                        isActive
                          ? "text-primary"
                          : "text-muted-foreground hover:text-foreground"
                      }
                    >
                      {tab.name}
                    </span>
                    {isActive && (
                      <motion.div
                        layoutId="activeTab"
                        className="absolute inset-0 bg-primary/10 rounded-lg -z-10"
                        transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                      />
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-hidden">
        <div className="container mx-auto px-4 py-8 h-full">{children}</div>
      </main>
    </div>
  );
};

export default Shell;
