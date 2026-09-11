import { MsEdgeTTS, OUTPUT_FORMAT } from 'msedge-tts';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const outputPath = path.resolve(__dirname, '../public/assets/baba-test.mp3');

const PROVIDER = 'Microsoft Azure Neural TTS (via Edge Neural protocol)';
const MODEL = 'Neural Multi-Lingual Speech Synthesizer';
const VOICE = 'Prabhat (Indian English, Mature Male)';
const VOICE_ID = 'en-IN-PrabhatNeural';
const PITCH = '-8Hz'; // Deep mature Ayurvedic scholar resonance
const RATE = '-10%';  // 0.90x deliberate scholarly cadence
const AUDIO_FORMAT = 'audio/mpeg (MP3, 24kHz, 48kbps mono)';

const TEST_INPUT = `Namaste. I am Baba Ji.

Tell me about your Ayurvedic formulation.

I will carefully examine the relevant traditional knowledge,
intellectual property provisions, and authoritative sources
before giving you an answer.`;

console.log('==================================================');
console.log('BABA JI NEURAL TTS VERIFICATION TEST');
console.log('==================================================');
console.log(`PROVIDER:        ${PROVIDER}`);
console.log(`MODEL:           ${MODEL}`);
console.log(`VOICE:           ${VOICE}`);
console.log(`VOICE ID:        ${VOICE_ID}`);
console.log(`PITCH:           ${PITCH} (Mature 70-80yo scholar tone)`);
console.log(`RATE:            ${RATE} (0.90x articulate delivery)`);
console.log(`AUDIO FORMAT:    ${AUDIO_FORMAT}`);
console.log(`OUTPUT PATH:     ${outputPath}`);
console.log('--------------------------------------------------');
console.log(`INPUT TEXT:\n"${TEST_INPUT}"\n`);
console.log('Connecting to Neural TTS service...');

const startTime = Date.now();
const tts = new MsEdgeTTS();
await tts.setMetadata(VOICE_ID, OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3);

const { audioStream } = tts.toStream(TEST_INPUT, {
  pitch: PITCH,
  rate: RATE,
  volume: '+0%'
});

const writeStream = fs.createWriteStream(outputPath);
audioStream.pipe(writeStream);

writeStream.on('finish', () => {
  const elapsed = Date.now() - startTime;
  const stats = fs.statSync(outputPath);
  console.log('--------------------------------------------------');
  console.log('✓ TEST PASSED!');
  console.log(`✓ Audio successfully generated in ${elapsed}ms`);
  console.log(`✓ File size: ${stats.size} bytes (${(stats.size / 1024).toFixed(1)} KB)`);
  console.log(`✓ Validated new voice: ${VOICE_ID}`);
  console.log('==================================================');
});

writeStream.on('error', (err) => {
  console.error('✗ TEST FAILED with error:', err);
  process.exit(1);
});
