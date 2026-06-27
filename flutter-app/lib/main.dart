import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:image_picker/image_picker.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'VoxMed',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        fontFamily: 'serif',
        scaffoldBackgroundColor: const Color(0xFF140708), // Dark Maroon tint
        useMaterial3: true,
      ),
      home: const VoxMedHome(),
    );
  }
}

class VoxMedHome extends StatefulWidget {
  const VoxMedHome({super.key});

  @override
  State<VoxMedHome> createState() => _VoxMedHomeState();
}

class _VoxMedHomeState extends State<VoxMedHome> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // Connection Settings
  String _localBackendIp = '10.0.2.2'; // Default Android Emulator Loopback
  String _localBackendPort = '7860';
  String _cloudBackendIp = '51.20.32.187'; // Django Bulut VM IP
  String _cloudBackendPort = '8000';

  String get _localUrl => 'http://$_localBackendIp:$_localBackendPort';
  String get _cloudUrl => 'http://$_cloudBackendIp:$_cloudBackendPort';

  // Profile data
  String _allergies = '';
  String _medications = '';
  bool _isProfileLoading = false;

  // Scanner state
  XFile? _selectedImage;
  bool _isScanning = false;
  bool? _isSafe;
  String _scanExplanation = '';
  String _ocrText = '';

  // History state
  List<dynamic> _historyLogs = [];
  bool _isHistoryLoading = false;

  // Chat & Speech
  final TextEditingController _chatController = TextEditingController();
  final ScrollController _chatScrollController = ScrollController();
  final List<Map<String, String>> _chatHistory = [];
  bool _isChatLoading = false;

  final SpeechToText _speechToText = SpeechToText();
  final FlutterTts _flutterTts = FlutterTts();
  bool _speechEnabled = false;
  bool _isListening = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (_tabController.index == 2) {
        _fetchHistory();
      }
    });

    _initSpeechAndTts();
    _fetchProfile();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _chatController.dispose();
    _chatScrollController.dispose();
    _flutterTts.stop();
    super.dispose();
  }

  // Initialize Native TTS and Speech to Text
  void _initSpeechAndTts() async {
    try {
      _speechEnabled = await _speechToText.initialize(
        onStatus: (status) {
          if (status == 'done' || status == 'notListening') {
            setState(() => _isListening = false);
            // Auto-send recognized text if any
            if (_chatController.text.trim().isNotEmpty) {
              _sendChatMessage();
            }
          }
        },
        onError: (error) {
          setState(() => _isListening = false);
        },
      );
      
      // Setup TTS language to Turkish
      await _flutterTts.setLanguage("tr-TR");
      await _flutterTts.setSpeechRate(0.52); // Natural and clear speed
      setState(() {});
    } catch (e) {
      debugPrint("STT/TTS Initialization error: $e");
    }
  }

  void _speak(String text) async {
    if (text.isNotEmpty) {
      await _flutterTts.stop();
      await _flutterTts.speak(text);
    }
  }

  void _startListening() async {
    await _speechToText.listen(
      onResult: (result) {
        setState(() {
          _chatController.text = result.recognizedWords;
        });
      },
      localeId: "tr-TR",
    );
    setState(() => _isListening = true);
  }

  void _stopListening() async {
    await _speechToText.stop();
    setState(() => _isListening = false);
  }

  // Django API: Fetch User Profile
  Future<void> _fetchProfile() async {
    setState(() => _isProfileLoading = true);
    try {
      final response = await http.get(Uri.parse('$_cloudUrl/api/profile'))
          .timeout(const Duration(seconds: 8));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _allergies = data['allergies'] ?? '';
          _medications = data['medications'] ?? '';
        });
      }
    } catch (e) {
      _showSnackbar('Cloud Profile connection failed. Using local storage.', Colors.orange);
    } finally {
      setState(() => _isProfileLoading = false);
    }
  }

  // Django API: Save User Profile
  Future<void> _saveProfile(String allergies, String medications) async {
    setState(() => _isProfileLoading = true);
    try {
      final response = await http.post(
        Uri.parse('$_cloudUrl/api/profile'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'allergies': allergies,
          'medications': medications,
        }),
      ).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        setState(() {
          _allergies = allergies;
          _medications = medications;
        });
        _showSnackbar('Profil başarıyla güncellendi.', Colors.green);
      } else {
        _showSnackbar('Failed to update profile on Cloud.', Colors.red);
      }
    } catch (e) {
      _showSnackbar('Cloud sync failed. Profile saved locally.', Colors.orange);
      setState(() {
        _allergies = allergies;
        _medications = medications;
      });
    } finally {
      setState(() => _isProfileLoading = false);
    }
  }

  // Django API: Fetch Scan History
  Future<void> _fetchHistory() async {
    setState(() => _isHistoryLoading = true);
    try {
      final response = await http.get(Uri.parse('$_cloudUrl/api/scans'))
          .timeout(const Duration(seconds: 8));
      if (response.statusCode == 200) {
        setState(() {
          _historyLogs = jsonDecode(response.body);
        });
      }
    } catch (e) {
      _showSnackbar('Failed to fetch history logs from Cloud.', Colors.red);
    } finally {
      setState(() => _isHistoryLoading = false);
    }
  }

  // Pick image via Camera or Gallery
  Future<void> _pickImage(ImageSource source) async {
    final ImagePicker picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: source);
    if (image != null) {
      setState(() {
        _selectedImage = image;
        _isSafe = null;
        _scanExplanation = '';
        _ocrText = '';
        _chatHistory.clear();
      });
      _runAnalysisPipeline();
    }
  }

  // Pipeline execution: OCR (Local) -> Image Upload (Cloud) -> Analyze (Local) -> Save Log (Cloud)
  Future<void> _runAnalysisPipeline() async {
    if (_selectedImage == null) return;
    setState(() => _isScanning = true);
    _speak("Görsel taranıyor, lütfen bekleyin.");

    String imageUrl = '';
    String extractedText = '';

    try {
      final imageBytes = await _selectedImage!.readAsBytes();

      // Step 1: Run OCR on Local GPU Server
      var ocrRequest = http.MultipartRequest('POST', Uri.parse('$_localUrl/ocr'));
      ocrRequest.files.add(http.MultipartFile.fromBytes(
        'image',
        imageBytes,
        filename: 'scan.png',
      ));
      
      final ocrResponse = await ocrRequest.send().timeout(const Duration(seconds: 30));
      if (ocrResponse.statusCode == 200) {
        final ocrData = jsonDecode(await ocrResponse.stream.bytesToString());
        extractedText = ocrData['text'] ?? '';
      } else {
        throw Exception("OCR server returned error code ${ocrResponse.statusCode}");
      }

      if (extractedText.isEmpty) {
        setState(() {
          _isSafe = true;
          _scanExplanation = "Paket üzerinde okunabilir içerik metni bulunamadı.";
        });
        _speak(_scanExplanation);
        return;
      }

      // Step 2: Upload Image to S3 (Via Django Cloud Backend)
      var uploadRequest = http.MultipartRequest('POST', Uri.parse('$_cloudUrl/api/upload'));
      uploadRequest.files.add(http.MultipartFile.fromBytes(
        'image',
        imageBytes,
        filename: 'scan.png',
      ));
      
      final uploadResponse = await uploadRequest.send().timeout(const Duration(seconds: 25));
      if (uploadResponse.statusCode == 200) {
        final uploadData = jsonDecode(await uploadResponse.stream.bytesToString());
        imageUrl = uploadData['image_url'] ?? '';
      }

      // Step 3: Run SmolLM2 Safety Analysis on Local GPU Server
      final analyzeRes = await http.post(
        Uri.parse('$_localUrl/analyze'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'text': extractedText,
          'allergies': _allergies,
          'medications': _medications
        }),
      ).timeout(const Duration(seconds: 60));

      if (analyzeRes.statusCode == 200) {
        final analyzeData = jsonDecode(analyzeRes.body);
        final safe = analyzeData['safe'] ?? true;
        final explanation = analyzeData['explanation'] ?? '';

        setState(() {
          _isSafe = safe;
          _scanExplanation = explanation;
          _ocrText = extractedText;
        });

        // Trigger spoken alert feedback (TTS)
        _speak(explanation);

        // Step 4: Write Audit Log to Django Cloud Database
        await http.post(
          Uri.parse('$_cloudUrl/api/scans'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'image_url': imageUrl,
            'raw_text': extractedText,
            'safe': safe,
            'explanation': explanation
          }),
        ).timeout(const Duration(seconds: 10));

      } else {
        throw Exception("Analysis endpoint returned error code ${analyzeRes.statusCode}");
      }

    } catch (e) {
      _showSnackbar('İşlem başarısız: Sunucu bağlantı hatası.', Colors.red);
      setState(() {
        _isSafe = null;
        _scanExplanation = 'Sunucu bağlantı hatası oluştu. Lütfen bağlantılarınızı kontrol edin.';
      });
      _speak("Bağlantı hatası oluştu.");
    } finally {
      setState(() => _isScanning = false);
    }
  }

  // Interactive conversational chat about the last scanned product
  Future<void> _sendChatMessage() async {
    final text = _chatController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _chatHistory.add({'role': 'user', 'content': text});
      _chatController.clear();
      _isChatLoading = true;
    });
    _scrollToBottom();

    try {
      final response = await http.post(
        Uri.parse('$_localUrl/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'message': text,
          'text': _ocrText,
          'allergies': _allergies,
          'medications': _medications
        }),
      ).timeout(const Duration(seconds: 60));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final reply = data['response'] ?? '';
        setState(() {
          _chatHistory.add({'role': 'assistant', 'content': reply});
        });
        _speak(reply);
      } else {
        _showSnackbar('Chat response failed.', Colors.red);
      }
    } catch (e) {
      _showSnackbar('Flask connection failed.', Colors.red);
    } finally {
      setState(() => _isChatLoading = false);
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_chatScrollController.hasClients) {
        _chatScrollController.animateTo(
          _chatScrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showSnackbar(String message, Color bgColor) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message, style: const TextStyle(fontFamily: 'serif', color: Colors.white)),
        backgroundColor: bgColor,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  void _openSettingsDialog() {
    final localIpController = TextEditingController(text: _localBackendIp);
    final localPortController = TextEditingController(text: _localBackendPort);
    final cloudIpController = TextEditingController(text: _cloudBackendIp);
    final cloudPortController = TextEditingController(text: _cloudBackendPort);

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF240A0D),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(15),
            side: const BorderSide(color: Color(0xFF5A1E24)),
          ),
          title: const Row(
            children: [
              Icon(Icons.settings, color: Color(0xFF92080F)),
              SizedBox(width: 10),
              Text('Bağlantı Ayarları', style: TextStyle(fontFamily: 'serif', color: Colors.white)),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Local ML Server (Flask)', style: TextStyle(fontFamily: 'serif', fontWeight: FontWeight.bold, color: Color(0xFFD29E71))),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: TextField(
                        controller: localIpController,
                        style: const TextStyle(color: Colors.white),
                        decoration: const InputDecoration(labelText: 'IP Adresi', border: OutlineInputBorder()),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      flex: 2,
                      child: TextField(
                        controller: localPortController,
                        style: const TextStyle(color: Colors.white),
                        decoration: const InputDecoration(labelText: 'Port', border: OutlineInputBorder()),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                const Text('Cloud Server (Django)', style: TextStyle(fontFamily: 'serif', fontWeight: FontWeight.bold, color: Color(0xFFD29E71))),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: TextField(
                        controller: cloudIpController,
                        style: const TextStyle(color: Colors.white),
                        decoration: const InputDecoration(labelText: 'IP Adresi', border: OutlineInputBorder()),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      flex: 2,
                      child: TextField(
                        controller: cloudPortController,
                        style: const TextStyle(color: Colors.white),
                        decoration: const InputDecoration(labelText: 'Port', border: OutlineInputBorder()),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('İptal', style: TextStyle(fontFamily: 'serif', color: Colors.grey)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF92080F)),
              onPressed: () {
                setState(() {
                  _localBackendIp = localIpController.text.trim();
                  _localBackendPort = localPortController.text.trim();
                  _cloudBackendIp = cloudIpController.text.trim();
                  _cloudBackendPort = cloudPortController.text.trim();
                });
                Navigator.pop(context);
                _fetchProfile();
                _showSnackbar('Bağlantı ayarları güncellendi.', Colors.green);
              },
              child: const Text('Kaydet', style: TextStyle(fontFamily: 'serif', color: Colors.white)),
            ),
          ],
        );
      },
    );
  }

  // Tab View 1: Camera Scanner & AI Chat Dialogue
  Widget _buildScannerTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Image Selection / Display Box
          GestureDetector(
            onTap: () => _showImageSourceOptions(),
            child: Container(
              width: double.infinity,
              height: 220,
              decoration: BoxDecoration(
                color: Colors.black38,
                borderRadius: BorderRadius.circular(15),
                border: Border.all(
                  color: _isSafe == null
                      ? Colors.white24
                      : (_isSafe! ? Colors.green.withValues(alpha: 0.5) : Colors.red.withValues(alpha: 0.5)),
                  width: 2,
                ),
              ),
              clipBehavior: Clip.antiAlias,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  if (_selectedImage != null)
                    Image.file(File(_selectedImage!.path), fit: BoxFit.contain, width: double.infinity, height: double.infinity)
                  else
                    const Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.camera_alt, color: Color(0xFF92080F), size: 48),
                        SizedBox(height: 10),
                        Text(
                          'Taramak istediğiniz paketin fotoğrafını çekin.',
                          style: TextStyle(fontFamily: 'serif', color: Colors.white70, fontStyle: FontStyle.italic),
                        ),
                      ],
                    ),
                  if (_isScanning)
                    Container(
                      color: Colors.black54,
                      child: const Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            CircularProgressIndicator(valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF92080F))),
                            SizedBox(height: 10),
                            Text('VoxMed analiz ediyor...', style: TextStyle(fontFamily: 'serif', color: Colors.white)),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Analysis Output Box
          if (_scanExplanation.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: _isSafe == null
                    ? const Color(0xFF241517)
                    : (_isSafe! ? const Color(0xFF132A15) : const Color(0xFF381518)),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: _isSafe == null
                      ? const Color(0xFF5A1E24)
                      : (_isSafe! ? Colors.green : Colors.red),
                  width: 1,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        _isSafe == null ? Icons.info : (_isSafe! ? Icons.check_circle : Icons.warning),
                        color: _isSafe == null ? Colors.blue : (_isSafe! ? Colors.green : Colors.red),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        _isSafe == null ? 'Durum' : (_isSafe! ? 'TÜKETİLEBİLİR' : 'UYARI: TÜKETMEYİN'),
                        style: TextStyle(
                          fontFamily: 'serif',
                          fontWeight: FontWeight.bold,
                          color: _isSafe == null ? Colors.blue : (_isSafe! ? Colors.green : Colors.red),
                          fontSize: 16,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(_scanExplanation, style: const TextStyle(fontFamily: 'serif', color: Colors.white70, height: 1.4)),
                ],
              ),
            ),
          const SizedBox(height: 20),

          // Chat Dialogue Output Title
          const Text('Sorularınız ve Detaylar', style: TextStyle(fontFamily: 'serif', fontSize: 18, color: Colors.white)),
          const SizedBox(height: 8),

          // Chat Dialogue Box
          Container(
            width: double.infinity,
            height: 180,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.black26,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF4A191C), width: 1),
            ),
            child: _chatHistory.isEmpty
                ? const Center(
                    child: Text(
                      'Taramadan sonra ürünle ilgili sorularınızı sorabilirsiniz.',
                      style: TextStyle(fontFamily: 'serif', color: Colors.white30, fontStyle: FontStyle.italic),
                    ),
                  )
                : ListView.builder(
                    controller: _chatScrollController,
                    itemCount: _chatHistory.length + (_isChatLoading ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == _chatHistory.length) {
                        return const Align(
                          alignment: Alignment.centerLeft,
                          child: Padding(
                            padding: EdgeInsets.symmetric(vertical: 4.0),
                            child: SizedBox(
                              width: 14,
                              height: 14,
                              child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF92080F))),
                            ),
                          ),
                        );
                      }
                      final msg = _chatHistory[index];
                      final isUser = msg['role'] == 'user';
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4.0),
                        child: RichText(
                          text: TextSpan(
                            style: const TextStyle(fontFamily: 'serif', fontSize: 14, height: 1.4),
                            children: [
                              TextSpan(
                                text: isUser ? 'SEN: ' : 'VOXMED: ',
                                style: TextStyle(fontWeight: FontWeight.bold, color: isUser ? const Color(0xFFD29E71) : const Color(0xFF92080F)),
                              ),
                               TextSpan(text: msg['content'], style: const TextStyle(color: Colors.white70)),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
          const SizedBox(height: 12),

          // Speech Chat Input Row
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF240A0D),
                    borderRadius: BorderRadius.circular(30),
                    border: Border.all(color: const Color(0xFF5A1E24), width: 1),
                  ),
                  child: TextField(
                    controller: _chatController,
                    style: const TextStyle(fontFamily: 'serif', color: Colors.white, fontSize: 15),
                    decoration: const InputDecoration(
                      hintText: 'Yazın veya sesli sorun...',
                      hintStyle: TextStyle(color: Colors.white30, fontStyle: FontStyle.italic),
                      border: InputBorder.none,
                    ),
                    onSubmitted: (_) => _sendChatMessage(),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              // Mic Icon Button
              GestureDetector(
                onTap: () {
                  if (!_speechEnabled) return;
                  if (_isListening) {
                    _stopListening();
                  } else {
                    _startListening();
                  }
                },
                child: CircleAvatar(
                  backgroundColor: _isListening ? Colors.red : const Color(0xFF92080F),
                  radius: 22,
                  child: Icon(_isListening ? Icons.mic : Icons.mic_none, color: Colors.white, size: 22),
                ),
              ),
              const SizedBox(width: 8),
              // Send Icon Button
              GestureDetector(
                onTap: _sendChatMessage,
                child: const CircleAvatar(
                  backgroundColor: Color(0xFF92080F),
                  radius: 22,
                  child: Icon(Icons.send, color: Colors.white, size: 18),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showImageSourceOptions() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF240A0D),
      builder: (context) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.camera_alt, color: Color(0xFF92080F)),
                title: const Text('Kamera', style: TextStyle(fontFamily: 'serif', color: Colors.white)),
                onTap: () {
                  Navigator.pop(context);
                  _pickImage(ImageSource.camera);
                },
              ),
              ListTile(
                leading: const Icon(Icons.photo_library, color: Color(0xFF92080F)),
                title: const Text('Galeri', style: TextStyle(fontFamily: 'serif', color: Colors.white)),
                onTap: () {
                  Navigator.pop(context);
                  _pickImage(ImageSource.gallery);
                },
              ),
            ],
          ),
        );
      },
    );
  }

  // Tab View 2: Health Profile Settings
  Widget _buildProfileTab() {
    final allergiesController = TextEditingController(text: _allergies);
    final medicationsController = TextEditingController(text: _medications);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Sağlık Profiliniz',
            style: TextStyle(fontFamily: 'serif', fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 8),
          const Text(
            'Taratacağınız ürünlerde kontrol edilmesini istediğiniz alerjilerinizi ve düzenli kullandığınız ilaçları buraya girin.',
            style: TextStyle(fontFamily: 'serif', color: Colors.white70, fontSize: 13, height: 1.4),
          ),
          const SizedBox(height: 24),
          
          const Text('Alerjileriniz (Virgülle ayırın)', style: TextStyle(fontFamily: 'serif', fontWeight: FontWeight.bold, color: Color(0xFFD29E71))),
          const SizedBox(height: 8),
          TextField(
            controller: allergiesController,
            style: const TextStyle(color: Colors.white),
            maxLines: 2,
            decoration: const InputDecoration(
              hintText: 'Örn: fıstık, gluten, laktoz, çilek',
              hintStyle: TextStyle(color: Colors.white30, fontStyle: FontStyle.italic),
              border: OutlineInputBorder(),
              focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: Color(0xFF92080F))),
            ),
          ),
          const SizedBox(height: 20),

          const Text('Kullandığınız İlaçlar (Virgülle ayırın)', style: TextStyle(fontFamily: 'serif', fontWeight: FontWeight.bold, color: Color(0xFFD29E71))),
          const SizedBox(height: 8),
          TextField(
            controller: medicationsController,
            style: const TextStyle(color: Colors.white),
            maxLines: 2,
            decoration: const InputDecoration(
              hintText: 'Örn: aspirin, parasetamol',
              hintStyle: TextStyle(color: Colors.white30, fontStyle: FontStyle.italic),
              border: OutlineInputBorder(),
              focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: Color(0xFF92080F))),
            ),
          ),
          const SizedBox(height: 30),

          if (_isProfileLoading)
            const Center(child: CircularProgressIndicator(valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF92080F))))
          else
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF92080F),
                minimumSize: const Size(double.infinity, 48),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
              ),
              onPressed: () {
                _saveProfile(
                  allergiesController.text.trim(),
                  medicationsController.text.trim()
                );
              },
              child: const Text(
                'Kaydet ve Senkronize Et',
                style: TextStyle(fontFamily: 'serif', fontSize: 16, color: Colors.white, fontWeight: FontWeight.bold),
              ),
            ),
        ],
      ),
    );
  }

  // Tab View 3: Scan Audit History
  Widget _buildHistoryTab() {
    if (_isHistoryLoading) {
      return const Center(child: CircularProgressIndicator(valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF92080F))));
    }

    if (_historyLogs.isEmpty) {
      return const Center(
        child: Text(
          'Henüz taranmış ürün geçmişi yok.',
          style: TextStyle(fontFamily: 'serif', color: Colors.white30, fontStyle: FontStyle.italic, fontSize: 16),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      itemCount: _historyLogs.length,
      itemBuilder: (context, index) {
        final log = _historyLogs[index];
        final safe = log['safe'] ?? true;
        
        return Card(
          color: const Color(0xFF240A0D),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: safe ? Colors.green.withValues(alpha: 0.3) : Colors.red.withValues(alpha: 0.3)),
          ),
          margin: const EdgeInsets.symmetric(vertical: 8),
          clipBehavior: Clip.antiAlias,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Display product image if uploaded to S3
              if (log['image_url'] != null && log['image_url'].toString().isNotEmpty)
                Image.network(
                  log['image_url'],
                  height: 120,
                  width: double.infinity,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) => const SizedBox.shrink(),
                ),
              Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(safe ? Icons.check_circle : Icons.warning, color: safe ? Colors.green : Colors.red, size: 18),
                        const SizedBox(width: 8),
                        Text(
                          safe ? 'GÜVENLİ ÜRÜN' : 'TEHLİKELİ ÜRÜN',
                          style: TextStyle(
                            fontFamily: 'serif',
                            fontWeight: FontWeight.bold,
                            color: safe ? Colors.green : Colors.red,
                            fontSize: 14,
                          ),
                        ),
                        const Spacer(),
                        Text(
                          log['timestamp'] != null ? log['timestamp'].toString().substring(0, 10) : '',
                          style: const TextStyle(fontFamily: 'serif', color: Colors.white30, fontSize: 11),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      log['explanation'] ?? '',
                      style: const TextStyle(fontFamily: 'serif', color: Colors.white70, fontSize: 13, height: 1.4),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF140708),
        elevation: 0,
        title: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            RichText(
              text: const TextSpan(
                style: TextStyle(fontFamily: 'serif', fontSize: 24, letterSpacing: 1.5),
                children: [
                  TextSpan(text: 'VOX', style: TextStyle(color: Colors.white)),
                  TextSpan(text: 'MED', style: TextStyle(color: Color(0xFF92080F), fontWeight: FontWeight.bold)),
                ],
              ),
            ),
            const SizedBox(width: 10),
            IconButton(
              icon: const Icon(Icons.settings, color: Color(0xFF92080F), size: 20),
              onPressed: _openSettingsDialog,
            ),
          ],
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: const Color(0xFF92080F),
          labelColor: const Color(0xFF92080F),
          unselectedLabelColor: Colors.white54,
          labelStyle: const TextStyle(fontFamily: 'serif', fontWeight: FontWeight.bold),
          tabs: const [
            Tab(text: 'Tara & Sor', icon: Icon(Icons.camera_alt)),
            Tab(text: 'Profilim', icon: Icon(Icons.person_pin)),
            Tab(text: 'Geçmiş', icon: Icon(Icons.history)),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildScannerTab(),
          _buildProfileTab(),
          _buildHistoryTab(),
        ],
      ),
    );
  }
}
