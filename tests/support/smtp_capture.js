const http = require('node:http');
const net = require('node:net');

const messages = [];

const smtpServer = net.createServer((socket) => {
  let buffer = '';
  let inMessage = false;
  let messageContent = '';
  let recipient = '';

  socket.write('220 localhost ESMTP capture\r\n');

  socket.on('data', (data) => {
    buffer += data.toString('utf8');

    if (inMessage) {
      const endIndex = buffer.indexOf('\r\n.\r\n');
      if (endIndex < 0) {
        messageContent += buffer;
        buffer = '';
        return;
      }

      messageContent += buffer.slice(0, endIndex);
      buffer = buffer.slice(endIndex + 5);
      messages.push({ to: recipient, content: messageContent });
      messageContent = '';
      recipient = '';
      inMessage = false;
      socket.write('250 Message accepted for capture\r\n');
    }

    let newlineIndex = buffer.indexOf('\r\n');
    while (newlineIndex >= 0) {
      const line = buffer.slice(0, newlineIndex);
      buffer = buffer.slice(newlineIndex + 2);
      const command = line.toUpperCase();

      if (command.startsWith('EHLO') || command.startsWith('HELO')) {
        socket.write('250-localhost\r\n250 SIZE 10485760\r\n');
      } else if (command.startsWith('MAIL FROM:')) {
        socket.write('250 Sender accepted\r\n');
      } else if (command.startsWith('RCPT TO:')) {
        recipient = line.match(/<([^>]+)>/)?.[1] || '';
        socket.write('250 Recipient accepted\r\n');
      } else if (command === 'DATA') {
        inMessage = true;
        socket.write('354 End data with <CR><LF>.<CR><LF>\r\n');
      } else if (command === 'RSET') {
        recipient = '';
        socket.write('250 Reset\r\n');
      } else if (command === 'QUIT') {
        socket.write('221 Goodbye\r\n');
        socket.end();
        return;
      } else {
        socket.write('250 OK\r\n');
      }

      newlineIndex = buffer.indexOf('\r\n');
    }
  });
});

const httpServer = http.createServer((request, response) => {
  const url = new URL(request.url, 'http://127.0.0.1:8026');
  response.setHeader('Access-Control-Allow-Origin', '*');
  response.setHeader('Content-Type', 'application/json');

  if (url.pathname === '/health') {
    response.writeHead(200).end(JSON.stringify({ status: 'healthy' }));
    return;
  }

  if (url.pathname === '/messages') {
    const recipient = url.searchParams.get('to');
    const matchingMessages = messages.filter((message) => message.to === recipient);
    response.writeHead(200).end(JSON.stringify({ messages: matchingMessages }));
    return;
  }

  response.writeHead(404).end(JSON.stringify({ detail: 'Not found' }));
});

smtpServer.listen(1025, '127.0.0.1');
httpServer.listen(8026, '127.0.0.1');

function closeServers() {
  smtpServer.close();
  httpServer.close();
}

process.on('SIGINT', closeServers);
process.on('SIGTERM', closeServers);
