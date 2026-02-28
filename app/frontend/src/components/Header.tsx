import { LogOut, Menu } from "lucide-react";

type Props = {
  title: string;
  onToggleSidebar: () => void;
  onLogout: () => void;
};

export function Header({ title, onToggleSidebar, onLogout }: Props) {
  return (
    <header className="shrink-0 border-b border-neutral-200 bg-white px-4 py-3 flex items-center justify-between gap-2">
      <button
        type="button"
        onClick={onToggleSidebar}
        className="p-2 rounded-lg text-neutral-600 hover:bg-neutral-100"
        aria-label="Toggle sidebar"
      >
        <Menu className="w-5 h-5" />
      </button>
      <h1 className="text-lg font-semibold tracking-tight truncate flex-1 text-center">
        {title}
      </h1>
      <button
        type="button"
        onClick={onLogout}
        className="shrink-0 rounded-lg p-2 text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Log out"
      >
        <LogOut className="w-5 h-5" />
      </button>
    </header>
  );
}
