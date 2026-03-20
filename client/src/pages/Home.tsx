import { Terminal, Zap, Globe, Shield, BarChart3, Rocket, CheckCircle, Share2 } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <section className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-white to-purple-50 pt-20 pb-32">
        <div className="absolute inset-0 bg-grid-pattern opacity-5" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-100 text-blue-700 text-sm font-medium mb-8">
              <Zap className="w-4 h-4" />
              Agent-Ready Edition v2.0
            </div>
            
            <h1 className="text-5xl md:text-6xl font-bold text-gray-900 tracking-tight mb-6">
              Share your localhost
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600">
                in seconds
              </span>
            </h1>
            
            <p className="text-xl text-gray-600 mb-10 leading-relaxed">
              Tunnel lets you share any local URL via a public HTTPS link — 
              no client setup, no account required. Auto-expires on Ctrl+C.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-100 px-4 py-2 rounded-lg">
                <Terminal className="w-4 h-4" />
                <code className="font-mono">pip install tunnel-cli</code>
              </div>
            </div>
            
            <div className="mt-6 p-4 bg-gray-900 rounded-xl text-left max-w-lg mx-auto">
              <div className="flex gap-2 mb-3">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
              </div>
              <pre className="text-green-400 font-mono text-sm">
                <span className="text-gray-500">$</span> tunnel share 3000
                {'\n'}
                <span className="text-gray-600">  Public URL: https://abc123xy.tunnel.dev</span>
                {'\n'}
                <span className="text-gray-600">  Waiting for visitors...</span>
              </pre>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Rocket,
                title: 'Instant Setup',
                description: 'Run one command. Get a public URL in under 5 seconds. No account needed.',
              },
              {
                icon: Globe,
                title: 'Works Everywhere',
                description: 'Anyone can access your tunneled URL from any browser. No client required.',
              },
              {
                icon: Shield,
                title: 'Auto-Expiry',
                description: 'Press Ctrl+C and the tunnel is gone. No dangling sessions, no cleanup.',
              },
              {
                icon: BarChart3,
                title: 'Traffic Analytics',
                description: 'Real-time dashboard shows request logs, visitor countries, and latency.',
              },
              {
                icon: Terminal,
                title: 'CLI First',
                description: 'Built for developers. Rich terminal output with live request streaming.',
              },
              {
                icon: CheckCircle,
                title: 'Self-Hostable',
                description: 'Run on your own VPS. No vendor lock-in. Docker-ready from day one.',
              },
            ].map((feature, i) => (
              <div key={i} className="p-6 rounded-2xl border border-gray-100 hover:border-gray-200 hover:shadow-lg transition-all">
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
                  <feature.icon className="w-6 h-6 text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <h2 className="text-3xl font-bold mb-6">How it works</h2>
            <div className="space-y-4">
              {[
                { step: '1', title: 'Install CLI', cmd: 'pip install tunnel-cli' },
                { step: '2', title: 'Share your port', cmd: 'tunnel share 3000' },
                { step: '3', title: 'Share the URL', cmd: 'https://abc123xy.tunnel.dev' },
                { step: '4', title: 'Press Ctrl+C when done', cmd: 'Auto-cleanup!' },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-sm font-bold shrink-0">
                    {item.step}
                  </div>
                  <div>
                    <span className="text-gray-300">{item.title}: </span>
                    <code className="bg-gray-800 px-2 py-1 rounded text-green-400 font-mono text-sm">
                      {item.cmd}
                    </code>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <footer className="bg-white border-t py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2 text-gray-600">
              <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded flex items-center justify-center">
                <Share2 className="w-4 h-4 text-white" />
              </div>
              <span className="text-sm">Tunnel — Built by developers, for developers</span>
            </div>
            <div className="flex gap-6 text-sm text-gray-500">
              <a href="#" className="hover:text-gray-700">Documentation</a>
              <a href="#" className="hover:text-gray-700">GitHub</a>
              <a href="#" className="hover:text-gray-700">Twitter</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
