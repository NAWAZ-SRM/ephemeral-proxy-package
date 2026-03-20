import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Share2, User, LogOut } from 'lucide-react';
import HomePage from '@/pages/Home';
import TunnelPage from '@/pages/Tunnel';
import LoginPage from '@/pages/Login';
import MyTunnelsPage from '@/pages/MyTunnels';

function Navbar() {
  const location = useLocation();
  const isLoggedIn = !!localStorage.getItem('tunnel_token');

  return (
    <nav className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Share2 className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">Tunnel</span>
          </Link>

          <div className="flex items-center gap-6">
            <Link
              to="/"
              className={`text-sm font-medium transition-colors ${
                location.pathname === '/'
                  ? 'text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Home
            </Link>

            {isLoggedIn && (
              <Link
                to="/my-tunnels"
                className={`text-sm font-medium transition-colors ${
                  location.pathname === '/my-tunnels'
                    ? 'text-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                My Tunnels
              </Link>
            )}

            {isLoggedIn ? (
              <button
                onClick={() => {
                  localStorage.removeItem('tunnel_token');
                  window.location.href = '/';
                }}
                className="flex items-center gap-1 text-sm font-medium text-gray-600 hover:text-red-600 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            ) : (
              <Link
                to="/login"
                className="flex items-center gap-1 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
              >
                <User className="w-4 h-4" />
                Login
              </Link>
            )}

            <a
              href="https://github.com/nawaz/tunnel"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/t/:slug" element={<TunnelPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/my-tunnels" element={<MyTunnelsPage />} />
      </Routes>
    </div>
  );
}
