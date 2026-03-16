import { NavLink } from "react-router-dom";
import { LayoutDashboard, Wallet, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/accounts", label: "Comptes", icon: Wallet },
  { to: "/analytics", label: "Analytiques", icon: BarChart3 },
];

export function BottomNav() {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-surface border-t border-border flex">
      {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            cn(
              "flex-1 flex flex-col items-center gap-1 py-3 text-[10px] font-medium transition-colors duration-150",
              isActive ? "text-accent" : "text-text-muted"
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon size={20} className={isActive ? "text-accent" : "text-text-muted"} />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
