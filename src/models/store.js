const fs = require('fs');
const path = require('path');
const { dataDir } = require('../config/config');

fs.mkdirSync(dataDir, { recursive: true });

function file(name) {
  return path.join(dataDir, name);
}

function read(name, fallback = []) {
  if (!fs.existsSync(file(name))) return fallback;
  return JSON.parse(fs.readFileSync(file(name), 'utf8'));
}

function write(name, value) {
  fs.writeFileSync(file(name), JSON.stringify(value, null, 2));
}

module.exports = {
  users: () => read('users.json'),
  saveUsers: users => write('users.json', users),
  documents: () => read('documents.json'),
  saveDocuments: documents => write('documents.json', documents),
};
