document.addEventListener('DOMContentLoaded', () => {
    new SolitaireGame();
});

class Card {
    constructor(suit, value) {
        this.suit = suit;
        this.value = value;
        this.isFaceUp = false;
        this.color = (suit === '♥' || suit === '♦') ? 'red' : 'black';
        this.rank = this.getRank();
        this.element = this.createElement();
        this.element.cardObject = this; // Link DOM element back to the object
    }

    getRank() {
        const ranks = { 'A': 1, 'J': 11, 'Q': 12, 'K': 13 };
        return ranks[this.value] || parseInt(this.value, 10);
    }

    createElement() {
        const el = document.createElement('div');
        el.classList.add('card');
        el.dataset.suit = this.suit;
        el.dataset.value = this.value; // Value for pseudo-elements
        // No innerHTML needed, CSS handles it
        el.classList.add(this.color);
        return el;
    }

    flip(faceUp) {
        this.isFaceUp = faceUp;
        this.element.classList.toggle('face-up', this.isFaceUp);
        this.element.classList.toggle('face-down', !this.isFaceUp);
        this.element.draggable = this.isFaceUp;
    }
}

class SolitaireGame {
    constructor() {
        this.initDOMReferences();
        this.addEventListeners();
        this.resetGame();
    }

    initDOMReferences() {
        this.scoreElement = document.getElementById('score');
        this.movesElement = document.getElementById('moves');
        this.stockPileElement = document.querySelector('.stock');
        this.wastePileElement = document.querySelector('.waste');
        this.foundationElements = document.querySelectorAll('.foundation');
        this.tableauPileElements = document.querySelectorAll('.tableau-pile');
        this.newGameButton = document.getElementById('new-game-button');
        this.gameBoard = document.querySelector('.game-board');
        this.gameHeader = document.querySelector('.game-header');
        this.hintButton = document.getElementById('hint-button');
        this.difficultyRadios = document.querySelectorAll('input[name="difficulty"]');
        this.isGameWon = false;
    }

    addEventListeners() {
        this.stockPileElement.addEventListener('click', () => this.handleStockClick());
        this.newGameButton.addEventListener('click', () => this.resetGame());
        this.hintButton.addEventListener('click', () => this.showHint());
        const gameBoard = document.querySelector('.game-board');
        gameBoard.addEventListener('dragstart', (e) => this.handleDragStart(e));
        gameBoard.addEventListener('dragover', (e) => this.handleDragOver(e));
        gameBoard.addEventListener('dragenter', (e) => this.handleDragEnter(e));
        gameBoard.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        gameBoard.addEventListener('drop', (e) => this.handleDrop(e));
        document.addEventListener('dragend', (e) => this.handleDragEnd(e));
        document.addEventListener('dblclick', (e) => this.handleDoubleClick(e));
    }

    resetGame() {
        this.score = -52;
        this.moves = 0;
        this.isGameWon = false;
        this.draggedInfo = {};
        this.clearBoard();
        this.setDifficulty();

        const deck = this.createDeck();
        this.shuffleDeck(deck);

        this.tableau = Array.from({ length: 7 }, () => []);
        for (let i = 0; i < 7; i++) {
            for (let j = i; j < 7; j++) {
                this.tableau[j].push(deck.pop());
            }
        }
        this.tableau.forEach(pile => pile[pile.length - 1].flip(true));

        this.stock = deck;
        this.waste = [];
        this.foundations = Array.from({ length: 4 }, () => []);

        this.renderAll();
        this.updateUI();
    }

    setDifficulty() {
        const selected = document.querySelector('input[name="difficulty"]:checked');
        this.drawCount = selected ? parseInt(selected.value, 10) : 1;
        console.log(`Difficulty set: Draw ${this.drawCount}`);
    }

    clearBoard() {
        this.stockPileElement.innerHTML = '';
        this.wastePileElement.innerHTML = '';
        this.foundationElements.forEach(el => el.innerHTML = '');
        this.tableauPileElements.forEach(el => el.innerHTML = '');
        const winMsg = document.getElementById('win-message');
        if (winMsg) winMsg.remove();
    }

    createDeck() {
        const suits = ['♥', '♦', '♠', '♣'];
        const values = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
        return suits.flatMap(suit => values.map(value => new Card(suit, value)));
    }

    shuffleDeck(deck) {
        for (let i = deck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [deck[i], deck[j]] = [deck[j], deck[i]];
        }
    }

    renderAll() {
        this.renderPile(this.stock, this.stockPileElement, { faceDown: true });
        this.renderPile(this.waste, this.wastePileElement);
        this.foundations.forEach((pile, i) => this.renderPile(pile, this.foundationElements[i]));
        this.tableau.forEach((pile, i) => this.renderPile(pile, this.tableauPileElements[i], { staggered: true }));
    }

    renderPile(pileData, pileElement, options = {}) {
        pileElement.innerHTML = '';
        if (options.faceDown && pileData.length > 0) {
            pileData[pileData.length - 1].flip(false);
            pileElement.appendChild(pileData[pileData.length - 1].element);
        } else {
            pileData.forEach((card, i) => {
                if (options.staggered) {
                    card.element.style.top = `${i * 30}px`;
                } else {
                    card.element.style.top = '0';
                }
                pileElement.appendChild(card.element);
            });
        }
        pileElement.classList.toggle('empty', pileData.length === 0);
    }

    updateUI() {
        this.scoreElement.textContent = `Score: $${this.score}`;
        this.movesElement.textContent = `Moves: ${this.moves}`;
    }

    handleStockClick() {
        if (this.isGameWon) return;
        if (this.stock.length > 0) {
            // Draw 1 or 3 cards based on difficulty
            const numToDraw = Math.min(this.stock.length, this.drawCount);
            for (let i = 0; i < numToDraw; i++) {
                const card = this.stock.pop();
                card.flip(true);
                this.waste.push(card);
            }
        } else if (this.waste.length > 0) {
            this.stock = this.waste.reverse();
            this.waste = [];
            this.stock.forEach(card => card.flip(false));
            this.score -= 20;
        }
        this.moves++;
        this.renderAll();
        this.updateUI();
    }

    handleDragStart(e) {
        if (this.isGameWon) return;
        const cardElement = e.target.closest('.card');
        if (!cardElement || !cardElement.cardObject.isFaceUp) {
            e.preventDefault();
            return;
        }

        const pileElement = cardElement.parentElement;
        const pileData = this.getPileDataFromElement(pileElement);
        const cardIndex = pileData.findIndex(c => c === cardElement.cardObject);

        this.draggedInfo = {
            cards: pileData.slice(cardIndex),
            sourcePileData: pileData,
            sourcePileElement: pileElement
        };

        // Add dragging class to all dragged cards for visual feedback
        this.draggedInfo.cards.forEach(c => c.element.classList.add('dragging'));
        e.dataTransfer.effectAllowed = 'move';
    }

    handleDragOver(e) {
        e.preventDefault(); // Necessary to allow dropping
    }

    handleDragEnter(e) {
        const dropZone = e.target.closest('.foundation, .tableau-pile');
        if (!dropZone || !this.draggedInfo.cards) return;

        const targetPileData = this.getPileDataFromElement(dropZone);
        if (this.isValidMove(this.draggedInfo.cards[0], targetPileData)) {
            dropZone.classList.add('drag-over-valid');
        } else {
            dropZone.classList.add('drag-over-invalid');
        }
    }

    handleDragLeave(e) {
        const dropZone = e.target.closest('.foundation, .tableau-pile');
        if (!dropZone) return;
        dropZone.classList.remove('drag-over-valid', 'drag-over-invalid');
    }

    handleDrop(e) {
        if (this.isGameWon) return;
        const dropZone = e.target.closest('.stock, .waste, .foundation, .tableau-pile');
        if (!dropZone || !this.draggedInfo.cards) return;

        const targetPileData = this.getPileDataFromElement(dropZone);
        if (this.isValidMove(this.draggedInfo.cards[0], targetPileData)) {
            // Move is valid, perform the move
            const cardsToMove = this.draggedInfo.cards;
            const sourcePile = this.draggedInfo.sourcePileData;

            // Remove cards from source
            sourcePile.splice(sourcePile.length - cardsToMove.length);

            // Add cards to target
            cardsToMove.forEach(card => targetPileData.push(card));

            // Flip new top card on source pile if it's tableau
            if (sourcePile.length > 0 && this.draggedInfo.sourcePileElement.classList.contains('tableau-pile')) {
                const newlyRevealedCard = sourcePile[sourcePile.length - 1];
                if (!newlyRevealedCard.isFaceUp) {
                    newlyRevealedCard.flip(true);
                    this.showEncouragement('Revealed!', newlyRevealedCard.element);
                }
            }

            if (dropZone.classList.contains('foundation')) {
                this.score += 5;
                this.showEncouragement('Nice!', cardsToMove[0].element);
            }
            this.moves++;

            this.renderAll();
            this.updateUI();
            this.checkWinCondition();
        }
    }

    handleDragEnd(e) {
        this.draggedInfo.cards?.forEach(c => c.element.classList.remove('dragging'));
        document.querySelectorAll('.drag-over-valid, .drag-over-invalid').forEach(el => el.classList.remove('drag-over-valid', 'drag-over-invalid'));
        this.draggedInfo = {};
    }

    handleDoubleClick(e) {
        if (this.isGameWon) return;
        const cardElement = e.target.closest('.card');
        if (!cardElement || !cardElement.cardObject.isFaceUp) return;

        const card = cardElement.cardObject;
        const sourcePileElement = cardElement.parentElement;
        const sourcePileData = this.getPileDataFromElement(sourcePileElement);

        // Only allow double-click on the top card of a pile
        if (sourcePileData[sourcePileData.length - 1] !== card) return;

        for (const foundation of this.foundations) {
            if (this.isValidMove(card, foundation)) {
                sourcePileData.pop();
                foundation.push(card);

                if (sourcePileData.length > 0 && sourcePileElement.classList.contains('tableau-pile')) {
                    sourcePileData[sourcePileData.length - 1].flip(true);
                }

                this.score += 5;
                this.moves++;
                this.showEncouragement('Excellent!', card.element);
                this.renderAll();
                this.updateUI();
                this.checkWinCondition();
                return; // Exit after successful move
            }
        }
    }

    isValidMove(card, targetPile) {
        const topCard = targetPile[targetPile.length - 1];
        const isFoundation = Array.from(this.foundationElements).some(el => el.contains(topCard?.element) || el === this.getPileElementFromData(targetPile));
        const isTableau = Array.from(this.tableauPileElements).some(el => el.contains(topCard?.element) || el === this.getPileElementFromData(targetPile));

        if (isFoundation) {
            if (!topCard) {
                return card.rank === 1; // Must be an Ace
            } else {
                return card.suit === topCard.suit && card.rank === topCard.rank + 1;
            }
        }

        if (isTableau) {
            if (!topCard) {
                return card.rank === 13; // Must be a King
            } else {
                return card.color !== topCard.color && card.rank === topCard.rank - 1;
            }
        }
        return false;
    }

    getPileDataFromElement(element) {
        if (element.classList.contains('stock')) return this.stock;
        if (element.classList.contains('waste')) return this.waste;
        for (let i = 0; i < this.foundationElements.length; i++) {
            if (this.foundationElements[i] === element) return this.foundations[i];
        }
        for (let i = 0; i < this.tableauPileElements.length; i++) {
            if (this.tableauPileElements[i] === element) return this.tableau[i];
        }
        return [];
    }

    getPileElementFromData(data) {
        if (data === this.stock) return this.stockPileElement;
        if (data === this.waste) return this.wastePileElement;
        for (let i = 0; i < this.foundations.length; i++) {
            if (this.foundations[i] === data) return this.foundationElements[i];
        }
        for (let i = 0; i < this.tableau.length; i++) {
            if (this.tableau[i] === data) return this.tableauPileElements[i];
        }
        return null;
    }

    checkWinCondition() {
        const totalCardsInFoundations = this.foundations.reduce((sum, pile) => sum + pile.length, 0);
        if (totalCardsInFoundations === 52 && !this.isGameWon) {
            this.isGameWon = true;
            console.log('You win!'); // Keep console log for debugging

            // Display win message
            const winMessage = document.createElement('div');
            winMessage.id = 'win-message';
            winMessage.textContent = 'YOU WIN!';
            this.gameHeader.appendChild(winMessage);

            // Trigger card fall animation
            const allCards = this.foundations.flat().map(c => c.element);
            allCards.forEach((card, i) => {
                setTimeout(() => {
                    card.classList.add('falling');
                    // Randomize horizontal position and rotation for a better effect
                    card.style.setProperty('--random-x', `${Math.random() * 40 - 20}vw`);
                    card.style.setProperty('--random-rot', `${Math.random() * 720 - 360}deg`);
                }, i * 50); // Stagger the start of each animation
            });
        }
    }

    showEncouragement(text, targetElement) {
        const message = document.createElement('div');
        message.classList.add('encouragement-text');
        message.textContent = text;
        this.gameHeader.appendChild(message);

        // Remove the element after the animation finishes
        setTimeout(() => message.remove(), 2000);
    }

    showHint() {
        if (this.isGameWon) return;

        const hint = this.findHint();
        if (hint) {
            this.score -= 2; // Penalize for using a hint
            this.updateUI();

            hint.source.classList.add('hint-highlight');
            if (hint.destination) {
                hint.destination.classList.add('hint-highlight');
            }

            setTimeout(() => {
                hint.source.classList.remove('hint-highlight');
                if (hint.destination) {
                    hint.destination.classList.remove('hint-highlight');
                }
            }, 1500);
        } else {
            this.showEncouragement('No moves!', this.gameBoard);
        }
    }

    findHint() {
        // 1. Check for moves to foundation (from waste or tableau)
        const wasteCard = this.waste[this.waste.length - 1];
        if (wasteCard) {
            for (let i = 0; i < this.foundations.length; i++) {
                if (this.isValidMove(wasteCard, this.foundations[i])) {
                    return { source: wasteCard.element, destination: this.foundationElements[i] };
                }
            }
        }
        for (let i = 0; i < this.tableau.length; i++) {
            const tableauPile = this.tableau[i];
            const topCard = tableauPile[tableauPile.length - 1];
            if (topCard) {
                for (let j = 0; j < this.foundations.length; j++) {
                    if (this.isValidMove(topCard, this.foundations[j])) {
                        return { source: topCard.element, destination: this.foundationElements[j] };
                    }
                }
            }
        }

        // 2. Check for moves between tableau piles
        for (let i = 0; i < this.tableau.length; i++) {
            for (const card of this.tableau[i]) {
                if (card.isFaceUp) {
                    for (let j = 0; j < this.tableau.length; j++) {
                        if (i === j) continue; // Don't check move to its own pile
                        if (this.isValidMove(card, this.tableau[j])) {
                            return { source: card.element, destination: this.tableauPileElements[j] };
                        }
                    }
                }
            }
        }

        // 3. Check for waste card to tableau
        if (wasteCard) {
            for (let i = 0; i < this.tableau.length; i++) {
                if (this.isValidMove(wasteCard, this.tableau[i])) {
                    return { source: wasteCard.element, destination: this.tableauPileElements[i] };
                }
            }
        }

        // 4. If no moves, suggest drawing from stock
        if (this.stock.length > 0) {
            return { source: this.stockPileElement, destination: null };
        }

        return null; // No possible moves found
    }
}