import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { MsEdgeTTS, OUTPUT_FORMAT } from 'msedge-tts';

// Vite middleware plugin for /api/tts serving Microsoft Azure Neural Indian Scholar voice
function neuralTtsPlugin(): Plugin {
  return {
    name: 'neural-tts-server',
    configureServer(server) {
      server.middlewares.use('/api/tts', async (req, res) => {
        if (req.method === 'POST') {
          let body = '';
          req.on('data', (chunk) => {
            body += chunk;
          });
          req.on('end', async () => {
            try {
              const parsed = JSON.parse(body || '{}');
              const text = parsed.text;
              const rate = parsed.rate || '-10%';
              const pitch = parsed.pitch || '-8Hz';

              if (!text || typeof text !== 'string') {
                res.statusCode = 400;
                res.setHeader('Content-Type', 'application/json');
                res.end(JSON.stringify({ error: 'Text field required' }));
                return;
              }

              const tts = new MsEdgeTTS();
              // en-IN-PrabhatNeural: mature, articulate Indian scholar
              await tts.setMetadata('en-IN-PrabhatNeural', OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3);

              const { audioStream } = tts.toStream(text, {
                pitch,
                rate,
                volume: '+0%',
              });

              res.setHeader('Content-Type', 'audio/mpeg');
              res.setHeader('Cache-Control', 'public, max-age=86400');
              audioStream.pipe(res);
            } catch (err: any) {
              console.error('[Neural TTS Server] Generation error:', err);
              res.statusCode = 500;
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ error: err?.message || 'TTS Error' }));
            }
          });
        } else {
          res.statusCode = 405;
          res.end('Method Not Allowed');
        }
      });
    },
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    neuralTtsPlugin(),
  ],
});
