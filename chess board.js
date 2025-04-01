/**
 * Chess Learning Platform - Chessboard Extensions
 * This file contains extensions to the Chessboard.js library
 */

// Custom drag and drop handling to improve piece movement responsiveness
Chessboard.fenToObj = function(fen) {
    // Convert FEN string to board object
    if (!fen) return {};
    
    const fenParts = fen.split(' ');
    const position = {};
    let row = 8;
    let col = 0;
    
    const pieces = fenParts[0].split('');
    for (let i = 0; i < pieces.length; i++) {
        const piece = pieces[i];
        
        if (piece === '/') {
            row--;
            col = 0;
            continue;
        }
        
        if (!isNaN(parseInt(piece))) {
            col += parseInt(piece);
            continue;
        }
        
        const color = piece.toLowerCase() === piece ? 'b' : 'w';
        const pieceType = piece.toLowerCase();
        const square = 'abcdefgh'[col] + row;
        
        position[square] = color + pieceType;
        col++;
    }
    
    return position;
};

// Add arrow drawing capability to chessboard
Chessboard.prototype.drawArrow = function(from, to, color = 'red') {
    // Remove any existing arrows
    this.removeArrows();
    
    // Get square positions
    const fromSquare = $('.square-' + from);
    const toSquare = $('.square-' + to);
    
    if (!fromSquare.length || !toSquare.length) return;
    
    // Calculate positions
    const fromPosition = {
        left: fromSquare.offset().left + fromSquare.width() / 2,
        top: fromSquare.offset().top + fromSquare.height() / 2
    };
    
    const toPosition = {
        left: toSquare.offset().left + toSquare.width() / 2,
        top: toSquare.offset().top + toSquare.height() / 2
    };
    
    // Create SVG overlay if it doesn't exist
    let svgOverlay = $('#chessboard-arrow-overlay');
    if (!svgOverlay.length) {
        const boardElement = $('#chessboard');
        boardElement.css('position', 'relative');
        
        svgOverlay = $('<svg id="chessboard-arrow-overlay" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; z-index: 100;"></svg>');
        boardElement.append(svgOverlay);
        
        // Set SVG dimensions to match board
        svgOverlay.attr('width', boardElement.width());
        svgOverlay.attr('height', boardElement.height());
    }
    
    // Calculate relative positions within the board
    const boardOffset = $('#chessboard').offset();
    const relFromPosition = {
        x: fromPosition.left - boardOffset.left,
        y: fromPosition.top - boardOffset.top
    };
    
    const relToPosition = {
        x: toPosition.left - boardOffset.left,
        y: toPosition.top - boardOffset.top
    };
    
    // Calculate arrow dimensions
    const dx = relToPosition.x - relFromPosition.x;
    const dy = relToPosition.y - relFromPosition.y;
    const angle = Math.atan2(dy, dx) * 180 / Math.PI;
    const length = Math.sqrt(dx * dx + dy * dy);
    
    // Arrow head dimensions
    const arrowHeadLength = 15;
    const arrowHeadWidth = 8;
    
    // Shorten the arrow to not completely cover squares
    const shortenFactor = 0.8;
    const newLength = length * shortenFactor;
    const deltaLength = length - newLength;
    
    const newToX = relFromPosition.x + dx * (1 - deltaLength / length);
    const newToY = relFromPosition.y + dy * (1 - deltaLength / length);
    
    // Create arrow line
    const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    arrow.setAttribute('x1', relFromPosition.x);
    arrow.setAttribute('y1', relFromPosition.y);
    arrow.setAttribute('x2', newToX);
    arrow.setAttribute('y2', newToY);
    arrow.setAttribute('stroke', color);
    arrow.setAttribute('stroke-width', '3');
    arrow.setAttribute('marker-end', 'url(#arrowhead)');
    arrow.setAttribute('class', 'chess-arrow');
    
    // Create arrowhead marker if it doesn't exist
    let arrowMarker = document.getElementById('arrowhead');
    if (!arrowMarker) {
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        arrowMarker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        arrowMarker.setAttribute('id', 'arrowhead');
        arrowMarker.setAttribute('viewBox', '0 0 10 10');
        arrowMarker.setAttribute('refX', '5');
        arrowMarker.setAttribute('refY', '5');
        arrowMarker.setAttribute('markerWidth', arrowHeadWidth);
        arrowMarker.setAttribute('markerHeight', arrowHeadLength);
        arrowMarker.setAttribute('orient', 'auto-start-reverse');
        
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
        path.setAttribute('fill', color);
        
        arrowMarker.appendChild(path);
        defs.appendChild(arrowMarker);
        svgOverlay[0].appendChild(defs);
    } else {
        // Update arrowhead color
        arrowMarker.querySelector('path').setAttribute('fill', color);
    }
    
    // Add arrow to SVG
    svgOverlay[0].appendChild(arrow);
};

// Remove all arrows from the board
Chessboard.prototype.removeArrows = function() {
    $('.chess-arrow').remove();
};

// Highlight squares function
Chessboard.prototype.highlightSquares = function(squares, className = 'highlight') {
    // Remove existing highlights first
    $('.square-55d63').removeClass(className);
    
    // Add new highlights
    if (Array.isArray(squares)) {
        squares.forEach(square => {
            $(`.square-${square}`).addClass(className);
        });
    } else {
        $(`.square-${squares}`).addClass(className);
    }
};

// Extend the clear function to remove highlights and arrows
const originalClear = Chessboard.prototype.clear;
Chessboard.prototype.clear = function() {
    // Remove all highlights and arrows
    $('.square-55d63').removeClass('highlight-white highlight-black highlight-hint highlight-last-move');
    this.removeArrows();
    
    // Call the original clear function
    return originalClear.apply(this, arguments);
};
