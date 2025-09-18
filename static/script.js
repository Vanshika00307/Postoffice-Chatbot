document.addEventListener('DOMContentLoaded', function() {
    const chatbotButton = document.getElementById('chatbotButton');
    const chatbotWindow = document.getElementById('chatbotWindow');
    const closeChatbot = document.getElementById('closeChatbot');
    const userInput = document.getElementById('userInput');
    const sendMessage = document.getElementById('sendMessage');
    const chatbotMessages = document.getElementById('chatbotMessages');

    // Get the new quit button and modal elements
    const quitChatbot = document.getElementById('quitChatbot');
    const quitModal = document.getElementById('quitModal');
    const confirmQuit = document.getElementById('confirmQuit');
    const cancelQuit = document.getElementById('cancelQuit');
    const closeModalBtn = quitModal.querySelector('.close-modal-btn');
    const feedbackEmojis = quitModal.querySelectorAll('.emoji-btn');
  
    const resetButton = document.getElementById('resetChatbot');
    const stars = document.querySelectorAll('#starRating .star');
    const submitFeedback = document.getElementById('submitFeedback');
    let selectedRating = 0;

    // Handle star click
    stars.forEach(star => {
        star.addEventListener('click', function() {
            selectedRating = parseInt(this.getAttribute('data-value'));

            // Highlight stars
            stars.forEach((s, index) => {
                if (index < selectedRating) {
                    s.classList.add('selected');
                } else {
                    s.classList.remove('selected');
                }
            });

            // Enable submit button
            submitFeedback.disabled = false;
        });
    });

    // Handle feedback submit
    submitFeedback.addEventListener('click', function() {
        if (selectedRating > 0) {
            console.log(`Thanks for your feedback: ${selectedRating} star(s)`);

            // Close modal after submit
            quitModal.style.display = 'none';
            chatbotWindow.classList.remove('active');

            // Reset stars for next time
            stars.forEach(s => s.classList.remove('selected'));
            selectedRating = 0;
            submitFeedback.disabled = true;
        }
    });

    chatbotButton.addEventListener('click', function() {
        chatbotWindow.classList.toggle('active');
        if (chatbotWindow.classList.contains('active')) {
            setTimeout(() => {
                sendUserMessage('hi');
            }, 500);
        }
    });
    
    closeChatbot.addEventListener('click', function() {
        console.log("Close chatbot clicked. Showing feedback modal.");
        quitModal.style.display = 'block'; // Show star feedback modal
    });

    // Event listeners for the modal buttons
    confirmQuit.addEventListener('click', function() {
        console.log("Confirm quit button clicked. Resetting chat.");
        chatbotWindow.classList.remove('active');
        chatbotMessages.innerHTML = ''; // Clear chat history
        quitModal.style.display = 'none';
        // Send a reset message to the backend to clear the session
        fetchBotResponse('reset');
    });

    cancelQuit.addEventListener('click', function() {
        console.log("Cancel quit button clicked. Hiding modal.");
        quitModal.style.display = 'none';
    });

    // This is the new code to close the modal
    closeModalBtn.addEventListener('click', function() {
        console.log("Close modal button clicked. Hiding modal.");
        quitModal.style.display = 'none';
    });

    // Event listeners for feedback emojis
    feedbackEmojis.forEach(button => {
        button.addEventListener('click', function() {
            // Using a simple console log for now
            console.log(`Thanks for your feedback: ${button.textContent}`);
            quitModal.style.display = 'none';
            chatbotWindow.classList.remove('active');
        });
    });

    function addMessageToChat(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add(`${sender}-message`);
        messageDiv.innerHTML = `<p>${message}</p>`;
        chatbotMessages.appendChild(messageDiv);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }

    function createOptionButtons(options) {
        const existingOptions = chatbotMessages.querySelector('.bot-options');
        if (existingOptions) {
            existingOptions.remove();
        }

        const optionsDiv = document.createElement('div');
        optionsDiv.classList.add('bot-options');
        options.forEach(option => {
            const button = document.createElement('button');
            button.textContent = option.text;
            button.classList.add('option-button');
            button.addEventListener('click', () => {
                addMessageToChat(option.text, 'user');
                fetchBotResponse(option.value);
            });
            optionsDiv.appendChild(button);
        });
        chatbotMessages.appendChild(optionsDiv);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }

    function createLoadingMessage(messageText) {
        const loadingMessageDiv = document.createElement('div');
        loadingMessageDiv.classList.add('loading-message');
        loadingMessageDiv.innerHTML = `<p>${messageText}</p>`;
        chatbotMessages.appendChild(loadingMessageDiv);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        return loadingMessageDiv;
    }

    function removeLoadingMessage(loadingMessageDiv) {
        if (loadingMessageDiv) {
            loadingMessageDiv.remove();
        }
    }

    async function getLocationAndSendToServer() {
        const loadingMessage = createLoadingMessage("Please wait, getting your location...");

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                async(position) => {
                    const { latitude, longitude } = position.coords;
                    removeLoadingMessage(loadingMessage);
                    await fetchBotResponseWithLocation(latitude, longitude);
                },
                (error) => {
                    removeLoadingMessage(loadingMessage);
                    console.error("Geolocation error:", error);
                    addMessageToChat("I'm sorry, I couldn't get your location. Please try again or find an office by Pincode.", 'bot');
                }
            );
        } else {
            removeLoadingMessage(loadingMessage);
            addMessageToChat("I'm sorry, your browser does not support geolocation.", 'bot');
        }
    }

    async function fetchBotResponseWithLocation(latitude, longitude) {
        const loadingMessage = createLoadingMessage("Searching for nearby post offices...");
        try {
            const response = await fetch('/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: "find_office_by_location", latitude, longitude })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            removeLoadingMessage(loadingMessage);
            addMessageToChat(data.response, 'bot');
            if (data.options) {
                createOptionButtons(data.options);
            }

        } catch (error) {
            removeLoadingMessage(loadingMessage);
            console.error('Error fetching chatbot response with location:', error);
            addMessageToChat("Sorry, I'm having trouble connecting right now. Please try again later.", 'bot');
        }
    }

    async function fetchBotResponse(message) {
        if (message === 'find_office_by_location') {
            getLocationAndSendToServer();
            return;
        }

        // Handle reset message
        if (message === 'reset') {
            chatbotMessages.innerHTML = '';
            await fetch('/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: 'reset' })
            });
            sendUserMessage('hi');
            return;
        }

        try {
            const response = await fetch('/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: message })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();

            setTimeout(() => {
                addMessageToChat(data.response, 'bot');
                if (data.options) {
                    createOptionButtons(data.options);
                }
            }, 500);

        } catch (error) {
            console.error('Error fetching chatbot response:', error);
            setTimeout(() => {
                addMessageToChat("Sorry, I'm having trouble connecting right now. Please try again later.", 'bot');
            }, 500);
        }
    }

    function sendUserMessage(message = null) {
        const userMessage = message || userInput.value.trim();
        if (userMessage) {
            if (!message) {
                addMessageToChat(userMessage, 'user');
            }
            userInput.value = '';
            fetchBotResponse(userMessage);
        }
    }

    sendMessage.addEventListener('click', () => sendUserMessage());

    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendUserMessage();
        }
    });

    // Add event listener to the existing reset button
    resetButton.addEventListener('click', () => {
        fetchBotResponse('reset');
    });

    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
});