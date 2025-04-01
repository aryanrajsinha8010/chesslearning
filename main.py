from flask import Flask, render_template, jsonify, request
import os
import logging
import chess
import chess.engine
import chess.pgn
import io
import random
import threading
import time
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "chess-learning-platform-secret")

# Global variables to store active games
active_games = {}
engine_path = os.environ.get("STOCKFISH_PATH", "/usr/games/stockfish")
engine_lock = threading.Lock()

class ChessGameManager:
    """Manages chess games and engine interactions"""
    
    def __init__(self, engine_path):
        self.engine_path = engine_path
        self.engine = None
        self.init_engine()
    
    def init_engine(self):
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
            # Configure engine with optimal settings
            try:
                self.engine.configure({
                    "Skill Level": 20,
                    "Threads": 2,
                    "Hash": 128,
                })
            except chess.engine.EngineError:
                # Some engines don't support these options
                pass
            logging.info("Chess engine initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize chess engine: {e}")
            # Fallback to random move generator if engine fails
            self.engine = None
    
    def get_engine_move(self, board, difficulty=3):
        if not self.engine:
            return self.get_random_move(board)
        
        try:
            # Adjust time based on difficulty
            think_time = 0.5 * difficulty
            
            with engine_lock:  # Use lock to prevent concurrent engine access
                result = self.engine.play(
                    board,
                    chess.engine.Limit(time=think_time),
                    info=chess.engine.INFO_ALL
                )
            
            if result and result.move:
                return result.move
            return self.get_random_move(board)
        except Exception as e:
            logging.error(f"Engine error: {e}")
            return self.get_random_move(board)
    
    def get_random_move(self, board):
        legal_moves = list(board.legal_moves)
        if legal_moves:
            return random.choice(legal_moves)
        return None
    
    def analyze_position(self, board, depth=15):
        if not self.engine:
            return {"score": 0.0, "mate": None}
        
        try:
            with engine_lock:
                info = self.engine.analyse(board, chess.engine.Limit(depth=depth))
                
            score = info.get("score", None)
            if score:
                if score.is_mate():
                    mate = score.mate()
                    return {"score": None, "mate": mate}
                else:
                    cp = score.white().score() / 100.0
                    return {"score": cp, "mate": None}
            return {"score": 0.0, "mate": None}
        except Exception as e:
            logging.error(f"Analysis error: {e}")
            return {"score": 0.0, "mate": None}
    
    def get_best_move(self, board):
        if not self.engine:
            return self.get_random_move(board), "No engine available"
        
        try:
            with engine_lock:
                result = self.engine.play(
                    board,
                    chess.engine.Limit(depth=15),
                    info=chess.engine.INFO_ALL
                )
            
            move = result.move
            return move, self.explain_move(board, move)
        except Exception as e:
            logging.error(f"Best move error: {e}")
            return self.get_random_move(board), "Engine error"
    
    def explain_move(self, board, move):
        piece = board.piece_at(move.from_square)
        if not piece:
            return "Invalid move"
        
        piece_name = chess.piece_name(piece.piece_type).capitalize()
        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)
        
        explanation = f"{piece_name} from {from_sq} to {to_sq}"
        
        # Check if move is a capture
        if board.is_capture(move):
            captured = board.piece_at(move.to_square)
            if captured:
                captured_name = chess.piece_name(captured.piece_type)
                explanation += f", capturing {captured_name}"
        
        # Check if move gives check
        board_copy = board.copy()
        board_copy.push(move)
        if board_copy.is_check():
            explanation += ", giving check"
        
        return explanation
    
    def close(self):
        if self.engine:
            try:
                self.engine.quit()
            except:
                pass

# Initialize the game manager
game_manager = ChessGameManager(engine_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/new_game', methods=['POST'])
def new_game():
    data = request.json
    game_mode = data.get('mode', 'Play')
    human_is_white = data.get('color', 'white') == 'white'
    
    game_id = str(int(time.time()))
    board = chess.Board()
    
    active_games[game_id] = {
        'board': board,
        'mode': game_mode,
        'human_is_white': human_is_white,
        'difficulty': 3,
        'show_hints': True,
        'move_history': [],
        'last_engine_hint': None
    }
    
    # If player is black, make first move as white
    if not human_is_white and game_mode != 'Self-Practice':
        engine_move = game_manager.get_engine_move(board, 3)
        if engine_move:
            board.push(engine_move)
            active_games[game_id]['move_history'].append(board.san(engine_move))
    
    return jsonify({
        'gameId': game_id,
        'fen': board.fen(),
        'isCheck': board.is_check(),
        'isCheckmate': board.is_checkmate(),
        'isStalemate': board.is_stalemate(),
        'isGameOver': board.is_game_over(),
        'turn': 'white' if board.turn == chess.WHITE else 'black',
        'moveHistory': active_games[game_id]['move_history']
    })

@app.route('/api/move', methods=['POST'])
def make_move():
    data = request.json
    game_id = data.get('gameId')
    from_square = data.get('from')
    to_square = data.get('to')
    
    if not game_id or game_id not in active_games:
        return jsonify({'error': 'Invalid game ID'}), 400
    
    game = active_games[game_id]
    board = game['board']
    
    # Convert algebraic notation to square indices
    from_idx = chess.parse_square(from_square)
    to_idx = chess.parse_square(to_square)
    
    # Check if promotion is needed
    promotion = None
    piece = board.piece_at(from_idx)
    if piece and piece.piece_type == chess.PAWN:
        if (chess.square_rank(to_idx) == 7 and piece.color == chess.WHITE) or \
           (chess.square_rank(to_idx) == 0 and piece.color == chess.BLACK):
            promotion = chess.QUEEN
    
    # Create move object
    try:
        if promotion:
            move = chess.Move(from_idx, to_idx, promotion)
        else:
            move = chess.Move(from_idx, to_idx)
    except ValueError:
        return jsonify({'error': 'Invalid move format'}), 400
    
    # Check if move is legal
    if move not in board.legal_moves:
        return jsonify({'error': 'Illegal move'}), 400
    
    # Make the move
    san_move = board.san(move)
    board.push(move)
    game['move_history'].append(san_move)
    
    response = {
        'fen': board.fen(),
        'isCheck': board.is_check(),
        'isCheckmate': board.is_checkmate(),
        'isStalemate': board.is_stalemate(),
        'isGameOver': board.is_game_over(),
        'turn': 'white' if board.turn == chess.WHITE else 'black',
        'lastMove': {
            'from': from_square,
            'to': to_square,
            'san': san_move
        },
        'moveHistory': game['move_history']
    }
    
    # In Play mode, make engine move after human move
    if game['mode'] == 'Play' and not board.is_game_over():
        is_human_turn = (game['human_is_white'] and board.turn == chess.WHITE) or \
                        (not game['human_is_white'] and board.turn == chess.BLACK)
        
        if not is_human_turn:
            engine_move = game_manager.get_engine_move(board, game['difficulty'])
            if engine_move:
                engine_san = board.san(engine_move)
                board.push(engine_move)
                game['move_history'].append(engine_san)
                
                response.update({
                    'fen': board.fen(),
                    'isCheck': board.is_check(),
                    'isCheckmate': board.is_checkmate(),
                    'isStalemate': board.is_stalemate(),
                    'isGameOver': board.is_game_over(),
                    'turn': 'white' if board.turn == chess.WHITE else 'black',
                    'engineMove': {
                        'from': chess.square_name(engine_move.from_square),
                        'to': chess.square_name(engine_move.to_square),
                        'san': engine_san
                    },
                    'moveHistory': game['move_history']
                })
    
    # Get position evaluation
    eval_data = game_manager.analyze_position(board)
    response['evaluation'] = eval_data
    
    return jsonify(response)

@app.route('/api/hint', methods=['POST'])
def get_hint():
    data = request.json
    game_id = data.get('gameId')
    
    if not game_id or game_id not in active_games:
        return jsonify({'error': 'Invalid game ID'}), 400
    
    game = active_games[game_id]
    board = game['board']
    
    # Get engine's best move
    best_move, explanation = game_manager.get_best_move(board)
    
    if best_move:
        game['last_engine_hint'] = {
            'from': chess.square_name(best_move.from_square),
            'to': chess.square_name(best_move.to_square),
            'explanation': explanation
        }
        
        return jsonify({
            'hint': game['last_engine_hint']
        })
    else:
        return jsonify({'error': 'Could not generate hint'}), 400

@app.route('/api/analyze', methods=['POST'])
def analyze_position():
    data = request.json
    game_id = data.get('gameId')
    
    if not game_id or game_id not in active_games:
        return jsonify({'error': 'Invalid game ID'}), 400
    
    game = active_games[game_id]
    board = game['board']
    
    eval_data = game_manager.analyze_position(board)
    
    return jsonify({
        'evaluation': eval_data
    })

@app.route('/api/undo', methods=['POST'])
def undo_move():
    data = request.json
    game_id = data.get('gameId')
    
    if not game_id or game_id not in active_games:
        return jsonify({'error': 'Invalid game ID'}), 400
    
    game = active_games[game_id]
    board = game['board']
    
    # In Play mode, undo both engine and human moves
    if game['mode'] == 'Play':
        # Undo engine's move first (if board has moves)
        if len(board.move_stack) > 0:
            board.pop()
            if game['move_history']:
                game['move_history'].pop()
        
        # Then undo player's move
        if len(board.move_stack) > 0:
            board.pop()
            if game['move_history']:
                game['move_history'].pop()
    else:
        # Just undo the last move in other modes
        if len(board.move_stack) > 0:
            board.pop()
            if game['move_history']:
                game['move_history'].pop()
    
    return jsonify({
        'fen': board.fen(),
        'isCheck': board.is_check(),
        'isCheckmate': board.is_checkmate(),
        'isStalemate': board.is_stalemate(),
        'isGameOver': board.is_game_over(),
        'turn': 'white' if board.turn == chess.WHITE else 'black',
        'moveHistory': game['move_history']
    })

@app.route('/api/set_difficulty', methods=['POST'])
def set_difficulty():
    data = request.json
    game_id = data.get('gameId')
    difficulty = data.get('difficulty', 3)
    
    if not game_id or game_id not in active_games:
        return jsonify({'error': 'Invalid game ID'}), 400
    
    # Ensure difficulty is between 1-4
    difficulty = max(1, min(4, int(difficulty)))
    active_games[game_id]['difficulty'] = difficulty
    
    return jsonify({
        'success': True,
        'difficulty': difficulty
    })

@app.route('/api/coach_comment', methods=['POST'])
def get_coach_comment():
    data = request.json
    game_id = data.get('gameId')
    move_idx = data.get('moveIdx', -1)
    
    if not game_id or game_id not in active_games:
        return jsonify({'error': 'Invalid game ID'}), 400
    
    game = active_games[game_id]
    board = chess.Board()  # Start from initial position
    
    # Rebuild the board up to the specified move
    if move_idx == -1 and game['move_history']:
        move_idx = len(game['move_history']) - 1
    
    if move_idx < 0 or not game['move_history'] or move_idx >= len(game['move_history']):
        return jsonify({'error': 'Invalid move index'}), 400
    
    # Replay the game up to the specified move
    for i in range(move_idx):
        move_san = game['move_history'][i]
        try:
            move = board.parse_san(move_san)
            board.push(move)
        except ValueError:
            continue
    
    # Get the last move and make it
    last_move_san = game['move_history'][move_idx]
    last_move = board.parse_san(last_move_san)
    
    # Generate coaching comment
    comment = generate_coach_comment(board, last_move)
    
    return jsonify({
        'comment': comment
    })

def generate_coach_comment(board, move):
    """Generate coaching comments for a move"""
    # Make a copy of the board to analyze the move
    board_copy = board.copy()
    
    # Get piece info
    piece = board.piece_at(move.from_square)
    if not piece:
        return "Unable to analyze this move."
    
    piece_type = piece.piece_type
    piece_name = chess.piece_name(piece_type).capitalize()
    
    comments = []
    
    # Check if it's a capture
    is_capture = board.is_capture(move)
    captured_piece = board.piece_at(move.to_square)
    
    # Make the move on the copy to analyze position after
    board_copy.push(move)
    gives_check = board_copy.is_check()
    
    # Central control (e4, d4, e5, d5)
    central_squares = [chess.E4, chess.D4, chess.E5, chess.D5]
    moved_to_center = move.to_square in central_squares
    
    # Early development and castling
    is_development = piece_type in [chess.KNIGHT, chess.BISHOP] and chess.square_rank(move.from_square) in [0, 7]
    is_castling = piece_type == chess.KING and abs(move.from_square - move.to_square) == 2
    
    # Build comment
    if is_capture:
        captured_name = chess.piece_name(captured_piece.piece_type) if captured_piece else "piece"
        comments.append(f"Good capture! Taking the {captured_name} gains material advantage.")
    
    if gives_check:
        comments.append("Nice check! Putting pressure on the opponent's king.")
    
    if moved_to_center and piece_type in [chess.PAWN, chess.KNIGHT]:
        comments.append("Good central control! Controlling the center is important in chess.")
    
    if is_development and board.fullmove_number <= 10:
        comments.append("Good development! Getting your pieces into play early is a key principle.")
    
    if is_castling:
        comments.append("Good castling! This move protects your king and connects your rooks.")
    
    # If no specific comments, give general advice
    if not comments:
        if board.fullmove_number <= 10:
            comments.append("Remember to focus on development, central control, and king safety in the opening.")
        elif board.fullmove_number <= 25:
            comments.append("In the middlegame, look for tactical opportunities and strategic advantages.")
        else:
            comments.append("In the endgame, activate your king and try to promote your pawns.")
    
    return " ".join(comments)

@app.teardown_appcontext
def shutdown_engine(exception=None):
    game_manager.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

