import { NavLink } from "react-router-dom";
import { FileSearch, GitCompare, Upload, Database } from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Upload", icon: Upload, end: true },
  { to: "/facts", label: "Facts", icon: Database },
  { to: "/relationships", label: "Relationships", icon: GitCompare },
];

export default function Header() {
  return (
    <header className="sticky top-0 z-40 bg-card border-b border-border shadow-sm">
      <div className="page-container flex items-center justify-between h-14">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center">
            <FileSearch className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-foreground tracking-tight">
            Fact Knowledge Layer
          </span>
        </div>

        {/* Nav */}
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors
                ${
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
