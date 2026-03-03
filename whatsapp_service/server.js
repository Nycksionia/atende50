const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const app = express();

app.use(express.json());

const client = new Client({
    authStrategy: new LocalAuth()
});

client.on('qr', (qr) => qrcode.generate(qr, { small: true }));
client.on('ready', () => console.log('WhatsApp do Atende50+ está pronto!'));

// Esta rota o seu Python vai chamar
app.post('/enviar', async (req, res) => {
    let { numero, mensagem } = req.body;
    
    try {
        // 1. Limpa o número de qualquer caractere não numérico
        let numlimpo = numero.replace(/\D/g, '');

        // 2. Garante que comece com 55 para o servidor do WhatsApp reconhecer
        if (!numlimpo.startsWith('55')) {
            numlimpo = '55' + numlimpo;
        }

        let chatId = `${numlimpo}@c.us`;

        // 3. Valida se o número existe na rede do WhatsApp antes de enviar
        let isRegistered = await client.isRegisteredUser(chatId);

        // 4. Se não achou (comum com o 9 extra em alguns DDDs), tenta sem o 9
        if (!isRegistered && numlimpo.length === 13) {
            // Remove o 9 (o dígito na posição 4 após o 55 e o DDD)
            const semNono = numlimpo.substring(0, 4) + numlimpo.substring(5);
            chatId = `${semNono}@c.us`;
            isRegistered = await client.isRegisteredUser(chatId);
        }

        if (isRegistered) {
            await client.sendMessage(chatId, mensagem);
            console.log(`✅ Sucesso! Mensagem enviada para: ${chatId}`);
            res.json({ status: 'Sucesso' });
        } else {
            console.log(`❌ Número não localizado no WhatsApp: ${chatId}`);
            res.status(404).json({ error: 'Contato não registrado' });
        }
    } catch (err) {
        console.error(`💥 Erro fatal ao processar ${numero}:`, err);
        res.status(500).json({ error: err.message });
    }
});

client.initialize();
app.listen(3000, () => console.log('Servidor de mensagens na porta 3000'));