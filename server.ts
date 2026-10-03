import express from 'express';
import http from 'http';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';

const app = express();
const PORT = 3000;
const FLASK_PORT = 5000;
const FLASK_HOST = '127.0.0.1';

let flaskProcess: ChildProcess | null = null;
let isFlaskReady = false;

function startFlaskServer() {
  const rootDir = process.cwd();
  console.log(`[Proxy] Iniciando servidor Flask e SQLite local em http://${FLASK_HOST}:${FLASK_PORT}...`);

  const env = {
    ...process.env,
    PORT: String(FLASK_PORT),
    HOST: FLASK_HOST,
    FLASK_ENV: 'development',
    PYTHONUNBUFFERED: '1',
  };

  flaskProcess = spawn('python3', [path.join(rootDir, 'run.py')], {
    env,
    cwd: rootDir,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  flaskProcess.stdout?.on('data', (data) => {
    const text = data.toString();
    process.stdout.write(`[Flask] ${text}`);
    if (text.includes('Running on') || text.includes('Iniciando Portal de Notícias') || text.includes('http://')) {
      isFlaskReady = true;
    }
  });

  flaskProcess.stderr?.on('data', (data) => {
    const text = data.toString();
    process.stderr.write(`[Flask ERR] ${text}`);
    if (text.includes('Running on') || text.includes('Press CTRL+C')) {
      isFlaskReady = true;
    }
  });

  flaskProcess.on('exit', (code, signal) => {
    console.log(`[Proxy] Processo Flask encerrou com código ${code} / sinal ${signal}. Reiniciando em 2s...`);
    isFlaskReady = false;
    setTimeout(startFlaskServer, 2000);
  });
}

// Inicia Flask no carregamento
startFlaskServer();

// Health check para conferir se Flask já responde
function checkFlaskHealth(): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.request(
      {
        hostname: FLASK_HOST,
        port: FLASK_PORT,
        path: '/api/stats',
        method: 'GET',
        timeout: 1000,
      },
      (res) => {
        resolve(res.statusCode === 200);
      }
    );
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
    req.end();
  });
}

// Proxy transparente para todos os métodos e rotas do Flask
app.use((req, res) => {
  const options: http.RequestOptions = {
    hostname: FLASK_HOST,
    port: FLASK_PORT,
    path: req.originalUrl || req.url,
    method: req.method,
    headers: {
      ...req.headers,
      host: `localhost:${PORT}`,
      'x-forwarded-for': req.ip || req.socket.remoteAddress || '',
      'x-forwarded-proto': req.protocol,
      'x-forwarded-port': String(PORT),
    },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    // Repassar status code e headers da resposta Flask
    res.writeHead(proxyRes.statusCode || 200, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on('error', async (err) => {
    console.warn(`[Proxy] Erro de conexão com Flask (${err.message}). Verificando inicialização...`);
    const ready = await checkFlaskHealth();
    if (ready) {
      res.status(502).send('Erro temporário ao conectar com Flask. Por favor recarregue a página.');
    } else {
      res.status(200).send(`
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>Inicializando Portal de Notícias SQLite...</title>
          <meta http-equiv="refresh" content="2">
          <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-slate-900 text-white min-h-screen flex items-center justify-center p-4">
          <div class="max-w-md w-full bg-slate-800 rounded-2xl p-6 text-center border border-slate-700 shadow-xl">
            <div class="w-12 h-12 rounded-full border-4 border-sky-400 border-t-transparent animate-spin mx-auto mb-4"></div>
            <h2 class="text-lg font-bold text-sky-400 mb-2">Inicializando Servidor Flask & SQLite</h2>
            <p class="text-xs text-slate-400 mb-4 leading-relaxed">
              Criando tabelas locais e verificando banco em <code class="bg-slate-950 px-1 py-0.5 rounded text-sky-300">instance/database.sqlite3</code>...
            </p>
            <div class="text-[11px] text-slate-500 font-mono">
              Recarregando automaticamente a cada 2 segundos...
            </div>
          </div>
        </body>
        </html>
      `);
    }
  });

  // Repassar corpo da requisição (POST, PUT, etc.)
  req.pipe(proxyReq, { end: true });
});

// Finalização graciosa
process.on('SIGINT', () => {
  flaskProcess?.kill();
  process.exit();
});
process.on('SIGTERM', () => {
  flaskProcess?.kill();
  process.exit();
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[Proxy] Servidor Proxy Express escutando na porta ${PORT}, redirecionando para Flask na porta ${FLASK_PORT}.`);
});
