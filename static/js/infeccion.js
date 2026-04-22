// Nombre: infeccion.js
// Ubicación: static/js/
// Función: Motor de reglas y validaciones para el juego Infección (Ataxx).

window.getInfeccionValidMoves = function(board, startIdx, pNum) {
    let moves = [];
    let r = Math.floor(startIdx / 7);
    let c = startIdx % 7;

    for (let dr = -2; dr <= 2; dr++) {
        for (let dc = -2; dc <= 2; dc++) {
            if (dr === 0 && dc === 0) continue;
            let nr = r + dr;
            let nc = c + dc;
            
            if (nr >= 0 && nr < 7 && nc >= 0 && nc < 7) {
                let ni = nr * 7 + nc;
                if (board[ni] === 0) moves.push(ni); 
            }
        }
    }
    return moves;
};

window.getInfeccionConversions = function(board, targetIdx, pNum) {
    let conversions = [];
    let r = Math.floor(targetIdx / 7);
    let c = targetIdx % 7;
    let opp = pNum === 1 ? 2 : 1; 

    for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            let nr = r + dr;
            let nc = c + dc;
            
            if (nr >= 0 && nr < 7 && nc >= 0 && nc < 7) {
                let ni = nr * 7 + nc;
                if (board[ni] === opp) conversions.push(ni);
            }
        }
    }
    return conversions;
};