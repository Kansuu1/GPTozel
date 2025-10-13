#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  MM TRADING BOT PRO - CoinMarketCap & Telegram entegrasyonlu kripto analiz botu
  
  Özellikler:
  - Dashboard yenileme: 10 dakikada bir
  - RSI (14) ve MACD (12,26,9) göstergeleri - Sinyal üretiminde kullanılıyor
  - Fiyat alarmları: Sinyal üretilince otomatik alarm, hedef fiyata ulaşınca Telegram bildirimi
  - Signal geçmişi grafikleri
  - Minimal tasarım ve mobil uyumluluk
  - Coin Başına Fetch Interval & Status Yönetimi
  - Telegram ayarları yönetim sekmesi
  - Manuel fiyat override sistemi (opsiyonel)
  
  Fiyat Kaynağı: SADECE CoinMarketCap API (diğer kaynaklar kullanılmıyor)

backend:
  - task: "Coin başına fetch interval sistemi"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Fetch interval ve status alanları eklendi. Her coin için bağımsız async loop çalışıyor."
  
  - task: "Global coin data cache"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "coin_data_cache global dictionary oluşturuldu. En son çekilen veriler saklanıyor."
  
  - task: "Fetch status endpoint"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/fetch-status ve GET /api/coin/{symbol}/latest endpoint'leri çalışıyor."
  
  - task: "Analyzer cache entegrasyonu"
    implemented: true
    working: true
    file: "backend/analyzer.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Analyzer önce cache'den veri alıyor, yoksa API'den çekiyor. Sinyaller en son veri üzerinden."
  
  - task: "RSI ve MACD göstergeleri"
    implemented: true
    working: true
    file: "backend/indicators.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "RSI (14 periyot) ve MACD (12,26,9) hesaplanıyor. Sinyal üretiminde kullanılıyor."
  
  - task: "Fiyat geçmişi kaydetme"
    implemented: true
    working: true
    file: "backend/price_history.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Her veri çekiminde fiyat MongoDB'ye kaydediliyor. RSI/MACD için gerekli."
  
  - task: "Fiyat alarm sistemi"
    implemented: true
    working: true
    file: "backend/price_alarms.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Sinyal üretilince otomatik alarm oluşuyor. Hedef fiyata ulaşınca Telegram bildirimi gönderiliyor."
  
  - task: "API endpoints (indicators, alarms, chart)"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/indicators/{symbol}, GET /api/alarms, GET /api/signals/chart endpoint'leri çalışıyor."

frontend:
  - task: "Telegram entegrasyon sekmesi"
    implemented: true
    working: true
    file: "frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Telegram bot token ve chat ID manuel giriş sekmesi eklendi. Aktif alarmlar listesi gösteriliyor."
  
  - task: "Status toggle button (Active/Passive)"
    implemented: true
    working: true
    file: "frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Her coin için 🟢/⚫ status toggle button eklendi."
  
  - task: "Fetch interval input field"
    implemented: true
    working: true
    file: "frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Dakika cinsinden interval input eklendi."
  
  - task: "Son güncelleme zamanı gösterimi"
    implemented: true
    working: true
    file: "frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "time_ago alanı ile 'X dakika önce' formatında gösterim yapılıyor. 10 saniyede bir refresh."
  
  - task: "Sinyaller sekmesi - Coin dropdown filtresi"
    implemented: true
    working: true
    file: "frontend/src/App.js, frontend/src/App.css"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Coinler yan yana değil, 'Tümü' dropdown menüsünde gösteriliyor. Dropdown açılınca tüm coinler listeleniyor. Yeni coin eklendiğinde otomatik dropdown'da görünüyor. Dışarı tıklanınca kapanıyor. Dark mode uyumlu."

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "Sinyaller sekmesi - Coin dropdown filtresi test"
    - "Status toggle functionality test"
    - "Fetch interval değişikliği test"
    - "Son güncelleme zamanı güncelleme test"
    - "Cache sistemi test"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Fetch interval & status yönetimi özelliği tamamlandı ve kullanıcı geri bildirimleri uygulandı."
  - agent: "user"
    message: "Pasif coinler hala veri çekiyor. API loglarından BTC ve ETH pasif ama sürekli çağrı yapılıyor görünüyor."
  - agent: "main"
    message: "✅ SORUN ÇÖZÜLDÜ: 3 sistem birden çalışıyordu (price_tracker, interval-based analyzer, coin-based fetch). Price tracker ve interval-based analyzer devre dışı bırakıldı. Artık sadece coin-based fetch çalışıyor. Passive coinler tamamen atlanıyor. Loglar ve API testleri doğrulandı."
  - agent: "main"
    message: "✅ YENİ ÖZELLİK EKLENDI: Sinyaller sekmesinde coin filtresi dropdown'a çevrildi. Artık coinler yan yana değil, 'Tümü' yazan dropdown'dan seçiliyor. Dropdown açılınca tüm coinler listelenebiliyor. Yeni coin eklendiğinde otomatik dropdown'da görünüyor. Kullanıcı talebine göre implement edildi."
  - agent: "user"
    message: "Eski panelden sinyalleri import ettim ama teknik analiz başlamadı. Neden sıfırdan veri toplanıyor?"
  - agent: "main"
    message: "✅ SORUN ÇÖZÜLDÜ: coin_settings eksikti, eklendi. 546 signal verisi signal_history'ye import edilmişti ama price_history boştu. Signal verilerindeki fiyat bilgilerini (features.price) kullanarak 546 adet fiyat kaydını price_history'ye aktardım. Şimdi 4/5 coin için RSI/MACD çalışıyor: BTC (108 veri), ETH (43 veri), ADA (42 veri), SOL (70 veri). BNB eski panelde yoktu, yeni toplanıyor (3 veri)."