/**
 * Chess Learning Platform - Main Application
 * This file contains the main logic for the chess application interface
 */

// Global variables
let game = null;         // Chess.js game instance
let board = null;        // Chessboard.js instance
let gameId = null;       // Current game ID
let gameMode = 'Play';   // Current game mode
let playerColor = 'white'; // Player's color
let difficulty = 3;      // Difficulty level (1-4)
let boardOrientation = 'white'; // Board orientation
let currentHint = null;  // Current hint move
let moveSound = new Audio('https://assets.mixkit.co/active_storage/sfx/201/201.wav');
let captureSound = new Audio('https://assets.mixkit.co/active_storage/sfx/3197/3197.wav');

// Initialize the game
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Create empty chessboard
    const config = {
        position: 'start',
        draggable: true,
        pieceTheme: 'https://lichess1.org/assets/piece/cburnett/{piece}.svg',
        onDragStart: onDragStart,
        onDrop: onDrop,
        onMouseoutSquare: onMouseoutSquare,
        onMouseoverSquare: onMouseoverSquare,
        onSnapEnd: onSnapEnd
    };
    
    board = Chessboard('chessboard', config);
    
    // Resize board on window resize
    window.addEventListener('resize', board.resize);
    
    // Initialize chess.js
    game = new Chess();
    
    // Set up event listeners
    setupEventListeners();
    
    // Show the game settings modal initially
    const gameSettingsModal = new bootstrap.Modal(document.getElementById('gameSettingsModal'));
    gameSettingsModal.show();
}

/**
 * Set up event listeners for UI controls
 */
function setupEventListeners() {
    // New game button
    document.getElementById('newGameBtn').addEventListener('click', function() {
        const gameSettingsModal = new bootstrap.Modal(document.getElementById('gameSettingsModal'));
        gameSettingsModal.show();
    });
    
    // Start game button
    document.getElementById('startGameBtn').addEventListener('click', function() {
        // Get selected options
        gameMode = document.getElementById('gameMode').value;
        difficulty = document.getElementById('difficultyLevel').value;
        
        // Get player color selection
        const colorRadios = document.getElementsByName('playerColor');
        for (let i = 0; i < colorRadios.length; i++) {
            if (colorRadios[i].checked) {
                if (colorRadios[i].value === 'random') {
                    playerColor = Math.random() < 0.5 ? 'white' : 'black';
                } else {
                    playerColor = colorRadios[i].value;
                }
                break;
            }
        }
        
        // Initialize new game
        startNewGame();
        
        // Close the modal
        bootstrap.Modal.getInstance(document.getElementById('gameSettingsModal')).hide();
    });
    
    // Game mode changes
    document.getElementById('gameMode').addEventListener('change', function() {
        const colorSelectDiv = document.getElementById('colorSelectDiv');
        if (this.value === 'Self-Practice') {
            colorSelectDiv.style.display = 'none';
        } else {
            colorSelectDiv.style.display = 'block';
        }
    });
    
    // Flip board button
    document.getElementById('flipBoardBtn').addEventListener('click', function() {
        boardOrientation = boardOrientation === 'white' ? 'black' : 'white';
        board.orientation(boardOrientation);
    });
    
    // Undo move button
    document.getElementById('undoMoveBtn').addEventListener('click', undoMove);
    
    // Hint button
    document.getElementById('hintBtn').addEventListener('click', getHint);
    
    // Suggest move button (practice mode)
    document.getElementById('suggestMoveBtn').addEventListener('click', suggestMove);
    
    // Coach comment button (practice mode)
    document.getElementById('coachCommentBtn').addEventListener('click', getCoachComment);
}

/**
 * Start a new chess game
 */
function startNewGame() {
    // Reset the board
    board.position('start');
    game = new Chess();
    
    // Set board orientation based on player color
    if (gameMode !== 'Self-Practice') {
        boardOrientation = playerColor;
        board.orientation(playerColor);
    }
    
    // Update UI for the selected game mode
    updateGameModeUI();
    
    // Create new game on server
    fetch('/api/new_game', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            mode: gameMode,
            color: playerColor,
            difficulty: difficulty
        })
    })
    .then(response => response.json())
    .then(data => {
        gameId = data.gameId;
        
        // If the server made a move (when playing as black), update the board
        if (data.fen !== 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1') {
            game.load(data.fen);
            board.position(game.fen());
            
            // Add to move history
            if (data.moveHistory && data.moveHistory.length > 0) {
                updateMoveHistory(data.moveHistory);
            }
        }
        
        // Update game status
        updateGameStatus(data);
    })
    .catch(error => {
        console.error('Error starting new game:', error);
        showError('Failed to start new game. Please try again.');
    });
}

/**
 * Update UI elements based on selected game mode
 */
function updateGameModeUI() {
    // Update game title
    const gameTitleMap = {
        'Play': 'Play vs AI',
        'Practice': 'Practice Mode',
        'Self-Practice': 'Self Practice'
    };
    document.getElementById('gameTitle').textContent = gameTitleMap[gameMode] || 'Chess Game';
    
    // Show/hide practice controls
    const practiceControls = document.getElementById('practiceControls');
    if (gameMode === 'Practice' || gameMode === 'Self-Practice') {
        practiceControls.style.display = 'block';
    } else {
        practiceControls.style.display = 'none';
    }
    
    // Update game status
    const statusText = gameMode === 'Play' ? 
        `Playing as ${playerColor}` : 
        (gameMode === 'Practice' ? 'Practice Mode - Make a move' : 'Self Practice - Play both sides');
    
    document.getElementById('gameStatus').textContent = statusText;
    document.getElementById('moveAnalysis').textContent = 'Make a move to see analysis';
}

/**
 * Handle piece drag start
 */
function onDragStart(source, piece, position, orientation) {
    // Don't allow piece movement if game is over
    if (game.game_over()) return false;
    
    // In Play mode, only allow moving your own pieces
    if (gameMode === 'Play') {
        // White pieces can only be moved by white player
        if (piece.search(/^w/) !== -1 && playerColor !== 'white') return false;
        
        // Black pieces can only be moved by black player
        if (piece.search(/^b/) !== -1 && playerColor !== 'white') return false;
    }
    
    // In Practice or Self-Practice mode, follow chess.js turn
    const whiteTurn = game.turn() === 'w';
    if ((whiteTurn && piece.search(/^b/) !== -1) || (!whiteTurn && piece.search(/^w/) !== -1)) {
        return false;
    }
    
    return true;
}

/**
 * Handle mouse hovering over squares
 */
function onMouseoverSquare(square, piece) {
    // Get list of possible moves for this square
    const moves = game.moves({
        square: square,
        verbose: true
    });
    
    // Exit if no moves available
    if (moves.length === 0) return;
    
    // Highlight the square
    highlightSquare(square);
    
    // Highlight possible moves
    for (let i = 0; i < moves.length; i++) {
        highlightSquare(moves[i].to);
    }
}

/**
 * Handle mouse leaving a square
 */
function onMouseoutSquare(square, piece) {
    removeHighlights();
}

/**
 * Highlight a square
 */
function highlightSquare(square) {
    const squareEl = $('#chessboard .square-' + square);
    
    // Add the highlight class
    if (squareEl.hasClass('black-3c85d')) {
        squareEl.addClass('highlight-black');
    } else {
        squareEl.addClass('highlight-white');
    }
}

/**
 * Remove all highlights
 */
function removeHighlights() {
    $('#chessboard .square-55d63').removeClass('highlight-white');
    $('#chessboard .square-55d63').removeClass('highlight-black');
    $('#chessboard .square-55d63').removeClass('highlight-hint');
    $('#chessboard .square-55d63').removeClass('highlight-last-move');
}

/**
 * Highlight the last move made
 */
function highlightLastMove(from, to) {
    // Remove existing highlights
    removeHighlights();
    
    // Highlight the squares
    const fromSquare = $('#chessboard .square-' + from);
    const toSquare = $('#chessboard .square-' + to);
    
    fromSquare.addClass('highlight-last-move');
    toSquare.addClass('highlight-last-move');
}

/**
 * Handle piece drop
 */
function onDrop(source, target) {
    // See if the move is legal
    const move = game.move({
        from: source,
        to: target,
        promotion: 'q' // Always promote to queen for simplicity
    });
    
    // If illegal move, return piece to source square
    if (move === null) return 'snapback';
    
    // Play move sound
    if (move.captured) {
        captureSound.play();
    } else {
        moveSound.play();
    }
    
    // Make the move on the server
    makeMove(source, target);
    
    // Highlight the move
    highlightLastMove(source, target);
}

/**
 * Called after piece snap animation completes
 */
function onSnapEnd() {
    // Update board position
    board.position(game.fen());
}

/**
 * Make a move on the server
 */
function makeMove(from, to) {
    if (!gameId) return;
    
    fetch('/api/move', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            gameId: gameId,
            from: from,
            to: to
        })
    })
    .then(response => response.json())
    .then(data => {
        // Update game status
        updateGameStatus(data);
        
        // Update move history
        if (data.moveHistory) {
            updateMoveHistory(data.moveHistory);
        }
        
        // Update evaluation
        if (data.evaluation) {
            updateEvaluation(data.evaluation);
        }
        
        // In Play mode, handle engine's move if available
        if (gameMode === 'Play' && data.engineMove) {
            // Update chess.js game
            game.move({
                from: data.engineMove.from,
                to: data.engineMove.to,
                promotion: 'q'
            });
            
            // Update board
            board.position(game.fen());
            
            // Play move sound
            if (data.engineMove.captured) {
                captureSound.play();
            } else {
                moveSound.play();
            }
            
            // Highlight the move
            highlightLastMove(data.engineMove.from, data.engineMove.to);
            
            // Show move analysis
            document.getElementById('moveAnalysis').textContent = 
                `Engine played: ${data.engineMove.san}`;
        }
    })
    .catch(error => {
        console.error('Error making move:', error);
        // Revert the move in the local game
        game.undo();
        // Update the board to reflect the correct position
        board.position(game.fen());
        // Show error message
        showError('Failed to make move. Please try again.');
    });
}

/**
 * Update the game status display
 */
function updateGameStatus(data) {
    const statusElement = document.getElementById('gameStatus');
    
    if (data.isCheckmate) {
        const winner = data.turn === 'white' ? 'Black' : 'White';
        statusElement.textContent = `Checkmate! ${winner} wins`;
        statusElement.className = 'alert alert-success';
    } else if (data.isStalemate) {
        statusElement.textContent = 'Game over! Stalemate';
        statusElement.className = 'alert alert-warning';
    } else if (data.isGameOver) {
        statusElement.textContent = 'Game over!';
        statusElement.className = 'alert alert-warning';
    } else if (data.isCheck) {
        statusElement.textContent = `${data.turn.charAt(0).toUpperCase() + data.turn.slice(1)} is in check`;
        statusElement.className = 'alert alert-danger';
    } else {
        statusElement.textContent = `${data.turn.charAt(0).toUpperCase() + data.turn.slice(1)}'s turn`;
        statusElement.className = 'alert alert-info';
    }
}

/**
 * Update the move history display
 */
function updateMoveHistory(moveHistory) {
    const historyElement = document.getElementById('moveHistory');
    historyElement.innerHTML = '';
    
    for (let i = 0; i < moveHistory.length; i += 2) {
        const moveNumber = Math.floor(i / 2) + 1;
        const whiteMove = moveHistory[i];
        const blackMove = i + 1 < moveHistory.length ? moveHistory[i + 1] : '';
        
        const moveElement = document.createElement('p');
        moveElement.innerHTML = `<strong>${moveNumber}.</strong> <span class="white-move">${whiteMove}</span> <span class="black-move">${blackMove}</span>`;
        historyElement.appendChild(moveElement);
    }
    
    // Scroll to bottom
    historyElement.scrollTop = historyElement.scrollHeight;
}

/**
 * Update the position evaluation display
 */
function updateEvaluation(evaluation) {
    const evalBar = document.getElementById('evaluationBar');
    const evalText = document.getElementById('evaluationText');
    
    if (evaluation.mate !== null) {
        // Mate evaluation
        const mateValue = evaluation.mate;
        if (mateValue > 0) {
            evalBar.style.width = '100%';
            evalText.textContent = `Mate in ${mateValue}`;
        } else {
            evalBar.style.width = '0%';
            evalText.textContent = `Mate in ${Math.abs(mateValue)}`;
        }
    } else if (evaluation.score !== null) {
        // Centipawn evaluation
        const score = evaluation.score;
        // Map score to width percentage (0% = -5 or lower, 100% = +5 or higher)
        let width = 50 + score * 10; // Each pawn worth 10%
        width = Math.max(0, Math.min(100, width));
        
        evalBar.style.width = width + '%';
        evalText.textContent = score > 0 ? `+${score.toFixed(1)}` : score.toFixed(1);
    }
}

/**
 * Get a hint from the engine
 */
function getHint() {
    if (!gameId || game.game_over()) return;
    
    fetch('/api/hint', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            gameId: gameId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.hint) {
            // Store the hint
            currentHint = data.hint;
            
            // Remove previous highlights
            removeHighlights();
            
            // Highlight the hint squares
            const fromSquare = $('#chessboard .square-' + data.hint.from);
            const toSquare = $('#chessboard .square-' + data.hint.to);
            
            fromSquare.addClass('highlight-hint');
            toSquare.addClass('highlight-hint');
            
            // Show hint explanation
            document.getElementById('moveAnalysis').textContent = 
                `Hint: ${data.hint.explanation}`;
        }
    })
    .catch(error => {
        console.error('Error getting hint:', error);
        showError('Failed to get hint');
    });
}

/**
 * Suggest a move in practice mode
 */
function suggestMove() {
    // This is the same as getting a hint
    getHint();
}

/**
 * Get a coaching comment for the last move
 */
function getCoachComment() {
    if (!gameId || game.history().length === 0) return;
    
    fetch('/api/coach_comment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            gameId: gameId,
            moveIdx: -1 // Get comment for last move
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.comment) {
            document.getElementById('moveAnalysis').innerHTML = 
                `<div class="coach-comment">${data.comment}</div>`;
        }
    })
    .catch(error => {
        console.error('Error getting coach comment:', error);
        showError('Failed to get coaching comment');
    });
}

/**
 * Undo the last move(s)
 */
function undoMove() {
    if (!gameId || game.history().length === 0) return;
    
    fetch('/api/undo', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            gameId: gameId
        })
    })
    .then(response => response.json())
    .then(data => {
        // Update local game and board
        game.load(data.fen);
        board.position(game.fen());
        
        // Update status and history
        updateGameStatus(data);
        
        if (data.moveHistory) {
            updateMoveHistory(data.moveHistory);
        }
        
        // Clear highlights
        removeHighlights();
        
        // Update analysis
        document.getElementById('moveAnalysis').textContent = 'Move undone';
    })
    .catch(error => {
        console.error('Error undoing move:', error);
        showError('Failed to undo move');
    });
}

/**
 * Display an error message
 */
function showError(message) {
    // Could be implemented with a toast or alert
    const gameStatus = document.getElementById('gameStatus');
    gameStatus.textContent = message;
    gameStatus.className = 'alert alert-danger';
    
    // Reset after a few seconds
    setTimeout(() => {
        updateGameStatus({
            turn: game.turn() === 'w' ? 'white' : 'black',
            isCheck: game.in_check(),
            isCheckmate: game.in_checkmate(),
            isStalemate: game.in_stalemate(),
            isGameOver: game.game_over()
        });
    }, 3000);
}
