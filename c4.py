def test_faults():
    x = 10
    
    # BUG 1: Identical comparison (Comparazione inutile)
    if x == x:
        print("Questo è sempre vero!")
        
    # BUG 2: Chiavi duplicate in un dizionario
    config = {
        "timeout": 30,
        "retry": 5,
        "timeout": 60  # Sovrascrittura involontaria
    }
    
    # BUG 3: Unreachable code (Codice irraggiungibile)
    return config
    print("Questo codice non verrà mai eseguito!")

test_faults()