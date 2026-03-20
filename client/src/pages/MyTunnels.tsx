import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Terminal, Plus } from 'lucide-react';

export default function MyTunnelsPage() {
  const navigate = useNavigate();
  const token = localStorage.getItem('tunnel_token');

  useEffect(() => {
    if (!token) {
      navigate('/login');
    }
  }, [token, navigate]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Tunnels</h1>
          <p className="text-gray-500 mt-1">Manage your active and recent tunnels.</p>
        </div>
        <a
          href="https://docs.tunnel.dev/cli"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Tunnel
        </a>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-12 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Terminal className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No active tunnels</h3>
          <p className="text-gray-500 mb-6 max-w-md mx-auto">
            You don't have any active tunnels yet. Install the CLI and run{' '}
            <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono">tunnel share 3000</code>{' '}
            to get started.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 px-4 py-2 rounded-lg">
              <span className="font-mono text-xs">pip install tunnel-cli</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Getting Started</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {[
            {
              step: '1',
              title: 'Install CLI',
              description: 'pip install tunnel-cli',
              code: true,
            },
            {
              step: '2',
              title: 'Share your port',
              description: 'tunnel share 3000 --ttl 2h',
              code: true,
            },
            {
              step: '3',
              title: 'Share the URL',
              description: 'Anyone can access via the HTTPS link',
              code: false,
            },
          ].map((item) => (
            <div key={item.step} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center text-xs font-bold text-blue-600">
                  {item.step}
                </div>
                <span className="font-medium text-gray-900">{item.title}</span>
              </div>
              <p className={`text-sm ${item.code ? 'font-mono text-gray-600' : 'text-gray-500'}`}>
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
