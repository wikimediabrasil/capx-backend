// Polyfill TextEncoder/TextDecoder for environments where they are missing (e.g., older Node + jsdom)
const { TextEncoder, TextDecoder } = require('util');

if (typeof global.TextEncoder === 'undefined') {
  global.TextEncoder = TextEncoder;
}
if (typeof global.TextDecoder === 'undefined') {
  global.TextDecoder = TextDecoder;
}

// Stub scrollTo for jsdom (override even if present)
if (typeof window !== 'undefined') {
  window.scrollTo = () => {};
}
