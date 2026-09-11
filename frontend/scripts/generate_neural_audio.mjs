import { MsEdgeTTS, OUTPUT_FORMAT } from 'msedge-tts';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const assetsDir = path.resolve(__dirname, '../public/assets');

const VOICE_ID = 'en-IN-PrabhatNeural'; // Mature, scholarly, authoritative Indian male voice
const PITCH = '-8Hz';                  // Lowers pitch to authentic 70-80 year old elder scholar resonance
const RATE = '-10%';                   // 0.90x deliberate, contemplative scholar cadence

const clips = [
  {
    name: 'baba-test.mp3',
    text: 'Namaste. I am Baba Ji. Tell me about your Ayurvedic formulation. I will carefully examine the relevant traditional knowledge, intellectual property provisions, and authoritative sources before giving you an answer.'
  },
  {
    name: 'baba-greeting.mp3',
    text: 'Namaste! I am Baba Ji, your Ayurvedic IP Assistant. Tell me about your formulation, or tap the mic to speak with me.'
  },
  {
    name: 'baba-clarification.mp3',
    text: 'That is an important question. Under Section 3(p) of the Indian Patents Act, traditional knowledge per se is non-patentable. To evaluate your claim against classical Samhitas, can you clarify: what exact modification have you made — an unexpected synergistic ratio, a novel extraction process, or a novel drug delivery carrier?'
  },
  {
    name: 'baba-answer-nano.mp3',
    text: 'Under Section 3(p) of the Indian Patents Act, traditional herbs themselves cannot be claimed. However, your novel drug delivery mechanism can overcome Section 3(p) and Section 3(d) if your claims are restricted to the inventive delivery matrix and comparative clinical data demonstrates significant bio-availability enhancement over classical decoctions.'
  },
  {
    name: 'baba-answer-synergism.mp3',
    text: 'Under Section 3(e) and 3(p), combining known classical herbs is deemed a mere aggregation unless you provide comparative in-vitro or in-vivo data proving true synergistic efficacy exceeding the additive sum of the individual herbs. Classical prior art in Charaka Samhita must be cited and distinguished.'
  },
  {
    name: 'baba-answer-extract.mp3',
    text: 'An isolated bioactive fraction or novel extraction method can be patented under Section 3(d) if you show distinct phytochemical characterization and an unexpected therapeutic enhancement over standard classical hydro-alcoholic extracts documented in the Ayurvedic Pharmacopoeia of India.'
  }
];

async function generateClips() {
  console.log(`[TTS Generator] Initializing Microsoft Azure Neural TTS with Voice: ${VOICE_ID} (Pitch: ${PITCH}, Rate: ${RATE})...`);

  for (const clip of clips) {
    const filePath = path.join(assetsDir, clip.name);
    console.log(`[TTS] Generating: ${clip.name}...`);

    const tts = new MsEdgeTTS();
    await tts.setMetadata(VOICE_ID, OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3);

    await new Promise((resolve, reject) => {
      const { audioStream } = tts.toStream(clip.text, {
        pitch: PITCH,
        rate: RATE,
        volume: '+0%'
      });

      const writeStream = fs.createWriteStream(filePath);
      audioStream.pipe(writeStream);

      writeStream.on('finish', () => {
        const stats = fs.statSync(filePath);
        console.log(`[TTS] ✓ Generated ${clip.name} (${(stats.size / 1024).toFixed(1)} KB)`);
        resolve(null);
      });

      writeStream.on('error', (err) => {
        console.error(`[TTS] ✗ Failed ${clip.name}:`, err);
        reject(err);
      });
    });
  }

  console.log('[TTS Generator] All neural audio clips successfully generated!');
}

generateClips().catch((err) => {
  console.error('[TTS Generator] Fatal error:', err);
  process.exit(1);
});
