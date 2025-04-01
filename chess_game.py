import chess
import chess.engine
import random
import logging
from typing import Optional, List, Dict, Any, Tuple

class StockfishError(Exception):
    """Exception raised for errors related to the Stockfish engine."""
    pass

class ChessGame:
    """Chess game implementation with AI integration."""
    
    def __init__(self, engine_path: str, mode: str):
        """Initialize a new chess game.
        
        Args:
            engine_path: Path to the chess engine executable
            mode: Game mode ('Play', 'Practice', or 'Self-Practice')
        """
        self.board = chess.Board()
        self.mode = mode
        self.engine = None
        self.difficulty_level = 3
        self.show_hints = True
        self.current_evaluation = "0.0"
        self.last_move = None
        self._move_cache = {}  # Cache for analyzed positions
        self.move_history = []
        
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)
            
            # Configure engine with optimal settings
            try:
                self.engine.configure({
                    "Skill Level": 20,
                    "Threads": 2,  # Adjust based on CPU
                    "Hash": 128,   # Memory in MB
                })
            except chess.engine.EngineError:
                # Some engines don't support these options
                logging.warning("Engine doesn't support all configuration options")
        except Exception as e:
            logging.error(f"Failed to start chess engine: {e}")
            # We'll continue without an engine and use fallback random moves
    
    def get_engine_move(self) -> Optional[chess.Move]:
        """Get the best move from the chess engine.
        
        Returns:
            A chess move object or None if no move could be determined
        """
        if self.board.is_game_over():
            return None
            
        try:
            board_fen = self.board.fen()
            if board_fen in self._move_cache:
                return self._move_cache[board_fen]
            
            if not self.engine:
                return self.get_random_move()
                
            result = self.engine.play(
                self.board,
                chess.engine.Limit(time=1.0),  # Increased from 0.5s
                info=chess.engine.INFO_ALL
            )
            
            if result is not None:
                move = result.move
                # Verify the move is legal before caching
                if move in self.board.legal_moves:
                    self._move_cache[board_fen] = move
                    return move
                else:
                    raise StockfishError(f"Illegal move suggested: {move}")
            else:
                raise StockfishError("Engine returned no move")
                
        except (chess.engine.EngineTerminatedError, StockfishError) as e:
            logging.error(f"Engine error: {e}")
            # Fallback: Random legal move
            return self.get_random_move()
    
    def get_random_move(self) -> Optional[chess.Move]:
        """Generate a random legal move.
        
        Returns:
            A random legal chess move or None if no moves are available
        """
        legal_moves = list(self.board.legal_moves)
        return random.choice(legal_moves) if legal_moves else None
    
    def get_practice_move(self) -> Optional[chess.Move]:
        """Get a move suggestion for practice mode.
        
        Returns:
            A suggested chess move for the current position
        """
        return self.get_engine_move()
    
    def analyze_position(self) -> str:
        """Analyze the current position and return evaluation.
        
        Returns:
            A string representing the position evaluation
        """
        try:
            if not self.engine:
                return "0.0"
                
            # Increase analysis time for more stable results
            info = self.engine.analyse(self.board, chess.engine.Limit(time=0.2))
            score = info.get("score", None)
            
            if score:
                if score.is_mate():
                    self.current_evaluation = f"Mate in {abs(score.mate())}"
                    return f"Mate in {abs(score.mate())}"
                else:
                    try:
                        cp = score.relative.score() / 100.0 if hasattr(score, "relative") else score.white().score() / 100.0
                        self.current_evaluation = f"{cp:.1f}"
                        return f"{cp:.1f} pawns"
                    except AttributeError as e:
                        logging.error(f"Score attribute error: {e}")
                        return "0.0"
            return "0.0"
        except Exception as e:
            logging.error(f"Analysis error: {e}")
            return "0.0"
    
    def get_coach_comment(self, move: chess.Move) -> str:
        """Provide a coaching comment on the move.
        
        Args:
            move: The chess move to comment on
            
        Returns:
            A string with coaching advice
        """
        comments = []
        
        # Check for captures
        if self.board.is_capture(move):
            comments.append("Good! Capturing pieces can help gain material advantage.")
        
        # Check for checks
        board_copy = self.board.copy()
        board_copy.push(move)
        if board_copy.is_check():
            comments.append("Nice check! Putting pressure on the opponent's king.")
        
        # Check for center control
        center_squares = [chess.E4, chess.D4, chess.E5, chess.D5]
        if move.to_square in center_squares:
            comments.append("Good move! Controlling the center is important in chess.")
        
        # Check for development in the opening
        piece = self.board.piece_at(move.from_square)
        if piece and piece.piece_type in [chess.KNIGHT, chess.BISHOP] and self.board.fullmove_number <= 10:
            comments.append("Good development! Getting your pieces into the game early is important.")
        
        # Check for castling
        if piece and piece.piece_type == chess.KING and abs(move.from_square - move.to_square) == 2:
            comments.append("Good castling! This move protects your king and connects your rooks.")
        
        # Default comment if none of the above apply
        if not comments:
            comments.append("Remember to develop your pieces and control the center.")
        
        return " ".join(comments)
    
    def set_difficulty(self, level: int) -> None:
        """Set the difficulty level for the AI.
        
        Args:
            level: Difficulty level (1-4)
        """
        self.difficulty_level = level
        if not self.engine:
            return
            
        skill_level = {
            1: 0,   # Beginner
            2: 5,   # Intermediate
            3: 10,  # Advanced
            4: 20   # Expert
        }.get(level, 10)
        
        try:
            self.engine.configure({"Skill Level": skill_level})
        except chess.engine.EngineError:
            # Some engines don't support this option
            logging.warning("Engine doesn't support skill level configuration")
    
    def make_move(self, move: chess.Move) -> bool:
        """Make a move on the board.
        
        Args:
            move: The chess move to make
            
        Returns:
            True if the move was successfully made, False otherwise
        """
        if move in self.board.legal_moves:
            san_move = self.board.san(move)
            self.board.push(move)
            self.last_move = move
            self.move_history.append(san_move)
            return True
        return False
    
    def undo_move(self) -> bool:
        """Undo the last move.
        
        Returns:
            True if a move was undone, False if no moves to undo
        """
        if self.board.move_stack:
            self.board.pop()
            if self.move_history:
                self.move_history.pop()
            return True
        return False
    
    def get_game_state(self) -> Dict[str, Any]:
        """Get the current state of the game.
        
        Returns:
            A dictionary with the current game state
        """
        return {
            "fen": self.board.fen(),
            "turn": "white" if self.board.turn == chess.WHITE else "black",
            "is_check": self.board.is_check(),
            "is_checkmate": self.board.is_checkmate(),
            "is_stalemate": self.board.is_stalemate(),
            "is_game_over": self.board.is_game_over(),
            "move_history": self.move_history,
            "evaluation": self.current_evaluation
        }
    
    def close(self) -> None:
        """Clean up resources by closing the engine."""
        if self.engine:
            try:
                self.engine.quit()
            except:
                pass
