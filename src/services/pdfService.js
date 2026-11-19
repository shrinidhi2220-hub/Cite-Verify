const fs = require('fs');
const { PDFParse } = require('pdf-parse');

async function fileToText(filePath) {
  const parser = new PDFParse({ data: fs.readFileSync(filePath) });
  try {
    const data = await parser.getText();
    return data.text || '';
  } finally {
    await parser.destroy();
  }
}

module.exports = { fileToText };
