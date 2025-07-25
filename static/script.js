const enterBtn = document.getElementById('enterBtn');
const micBtn = document.getElementById('micBtn');
const queryInput = document.getElementById('queryInput');
const resultsPanel = document.getElementById('resultsPanel');
const resultsList = document.getElementById('resultsList'); 

const socket = io('http://127.0.0.1:5000'); 

socket.on('connect', () => {
    console.log('Connected to backend WebSocket!');
    
});

socket.on('status', (data) => {
    console.log('Backend Status:', data.message);
});

socket.on('agent_response', (data) => {
    console.log('Agent Response (Text):', data.text);
    
    if (data.type !== 'speaking_intro') {
        updateResultsPanelWithText(data.text, 'agent'); 
    }
    
    speakText(data.text);
});

socket.on('email_snippets', (data) => {
    console.log('Email Snippets received:', data.snippets);
    
    resultsList.innerHTML = ''; 

    let fullTextToSpeak = "";

    data.snippets.forEach((snippet, index) => {
        const li = document.createElement('li');
        li.textContent = snippet;
        resultsList.appendChild(li);
        
        fullTextToSpeak += snippet + ". ... "; 
    });

    
    if (fullTextToSpeak) {
        speakText("Here are the emails: " + fullTextToSpeak); 
    }

    resultsPanel.style.display = 'block'; 
    resultsList.scrollTop = resultsList.scrollHeight; 
});


function speakText(text) {
    if ('speechSynthesis' in window) {
        
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US'; 
    
        utterance.onstart = () => {
            console.log('Speaking:', text);
            micBtn.classList.add('speaking'); 
        };
        utterance.onend = () => {
            console.log('Finished speaking.');
            micBtn.classList.remove('speaking');
        };
        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event.error);
        };
        window.speechSynthesis.speak(utterance);
    } else {
        console.warn('Web Speech API (SpeechSynthesis) not supported in this browser.');
    }
}


function updateResultsPanelWithText(text, sender) {
    const li = document.createElement('li');
    li.textContent = `${sender === 'user' ? 'You' : 'Agent'}: ${text}`; 
    resultsList.appendChild(li);
    resultsPanel.style.display = 'block'; 
    resultsList.scrollTop = resultsList.scrollHeight; 
}

function sendCommand() {
    const command = queryInput.value.trim();
    if (command) {
        console.log('Sending text command:', command);
        updateResultsPanelWithText(command, 'user'); 
        socket.emit('process_command_event', { command: command }); 
        queryInput.value = ''; 
    }
}

enterBtn.addEventListener('click', sendCommand);

queryInput.addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault(); 
        sendCommand(); 
    }
});

micBtn.addEventListener('click', () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Sorry, your browser does not support Speech Recognition.');
        return;
    }
    queryInput.value = "";  

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.start();
    micBtn.classList.add('listening'); 
    console.log('Listening for command...');

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        queryInput.value = transcript;
        console.log('Recognized speech:', transcript);

        updateResultsPanelWithText(transcript, 'user'); 
        socket.emit('process_command_event', { command: transcript });

        micBtn.classList.remove('listening'); 
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        micBtn.classList.remove('listening');
        updateResultsPanelWithText("Sorry, I could not understand your voice. Please try again.", 'agent');
        speakText("Sorry, I could not understand your voice. Please try again.");
    };

    recognition.onend = () => {
        micBtn.classList.remove('listening');
        console.log('Speech recognition session ended.');
    };
});