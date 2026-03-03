const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const app = express();

app.use(express.json());

// Ajustamos o caminho para './auth' porque você já está dentro da pasta whatsapp
const client = new Client({
    authStrategy: new LocalAuth({ clientId: "atende50", dataPath: './auth' }),
    puppeteer: { 
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        headless: true 
    }
});

client.on('qr', qr => {
    console.log('⚡ NOVO QR CODE GERADO:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => console.log('✅ Motor WhatsApp Atende50+ Pronto!'));

app.post('/enviar', async (req, res) => {
    let { fone, msg } = req.body;
    try {
        // Limpeza do número para garantir que o formato @c.us funcione
        let numeroLimpo = fone.replace(/\D/g, '');
        if (!numeroLimpo.startsWith('55')) numeroLimpo = '55' + numeroLimpo;
        
        const id = numeroLimpo + '@c.us';
        
        await client.sendMessage(id, msg);
        console.log(`🚀 Enviado para: ${numeroLimpo}`);
        res.status(200).send('Enviado');
    } catch (e) { 
        console.log('❌ ERRO NO MOTOR:', e.message); // Isso vai te mostrar o erro real no terminal
        res.status(500).send('Erro'); 
    }
});

client.initialize();
app.listen(3001, () => console.log('🚀 API de Mensagens rodando na porta 3001'));