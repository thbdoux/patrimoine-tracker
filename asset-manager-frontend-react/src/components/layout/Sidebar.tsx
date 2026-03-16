import { NavLink } from "react-router-dom";
import { LayoutDashboard, Wallet, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/accounts", label: "Comptes", icon: Wallet },
  { to: "/analytics", label: "Analytiques", icon: BarChart3 },
];

export function Sidebar() {
  return (
    <aside className="hidden md:flex flex-col w-[220px] shrink-0 bg-surface border-r border-border min-h-screen">
      {/* Logo */}
      <div className="px-5 py-6 mb-2">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-[10px] bg-gradient-to-br from-accent to-[#7c3aed] flex items-center justify-center">
            <span className="text-white text-sm font-bold">P</span>
          </div>
          <span className="text-text-primary font-semibold text-sm">Patrimoine</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors duration-150",
                isActive
                  ? "bg-accent/15 text-accent"
                  : "text-text-secondary hover:bg-elevated hover:text-text-primary"
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={16} className={isActive ? "text-accent" : ""} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
