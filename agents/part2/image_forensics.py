"""
ImageForensicsAgent - Advanced image analysis for embedded images in documents

Responsibilities:
1. Extract images from PDF documents
2. EXIF metadata analysis
3. AI-generated image detection
4. Reverse image search
5. Error Level Analysis (ELA) for tampering detection
6. Image quality and consistency checks
"""

import logging
import os
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from io import BytesIO
import json

from agents import Part2Agent

logger = logging.getLogger(__name__)


class ImageForensicsAgent(Part2Agent):
    """Agent: Advanced image forensics - AI detection, reverse search, tampering analysis"""

    def __init__(self, llm_service=None):
        super().__init__("image_forensics")
        self.llm_service = llm_service
        
        # Check for optional dependencies
        self._init_dependencies()

    def _init_dependencies(self):
        """Initialize optional image processing libraries"""
        # PIL/Pillow
        self.pil_available = False
        try:
            from PIL import Image, ImageChops, ImageStat
            self.Image = Image
            self.ImageChops = ImageChops
            self.ImageStat = ImageStat
            self.pil_available = True
            logger.info("PIL/Pillow available for image processing")
        except ImportError:
            logger.warning("PIL/Pillow not available - image analysis limited")

        # PyMuPDF for image extraction
        self.fitz_available = False
        try:
            import fitz
            self.fitz = fitz
            self.fitz_available = True
            logger.info("PyMuPDF available for image extraction")
        except ImportError:
            logger.warning("PyMuPDF not available - can't extract images from PDF")

        # ExifRead for metadata
        self.exif_available = False
        try:
            import exifread
            self.exifread = exifread
            self.exif_available = True
            logger.info("ExifRead available for EXIF analysis")
        except ImportError:
            logger.warning("ExifRead not available - EXIF analysis disabled")

        # OpenCV for advanced analysis
        self.cv2_available = False
        try:
            import cv2
            import numpy as np
            self.cv2 = cv2
            self.np = np
            self.cv2_available = True
            logger.info("OpenCV available for advanced image analysis")
        except ImportError:
            logger.warning("OpenCV not available - advanced analysis limited")

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute image forensics analysis.

        Args:
            state: Workflow state containing:
                - file_path: Path to document (PDF/JPG/PNG)
                - file_format: Format of file (pdf/jpg/png)
                - document_id: Unique document ID

        Returns:
            Updated state with:
                - images_analyzed: Number of images analyzed
                - ai_generated_detected: Boolean
                - ai_detection_confidence: 0-100
                - image_tampering_detected: Boolean
                - exif_issues: List of EXIF-related findings
                - reverse_search_results: List of matches
                - image_forensics_score: 0-100
        """
        self.logger.info("Executing ImageForensicsAgent")

        file_path = state.get("file_path")
        file_format = state.get("file_format", "pdf")
        document_id = state.get("document_id")
        errors = state.get("errors", [])

        # Initialize results
        images_analyzed = 0
        ai_generated_detected = False
        ai_detection_confidence = 0
        image_tampering_detected = False
        exif_issues = []
        reverse_search_results = []
        image_forensics_score = 100
        image_findings = []

        try:
            # Step 1: Get images based on format
            self.logger.info(f"🖼️  Processing {file_format.upper()} for image forensics...")
            
            if file_format == "pdf":
                images = self._extract_images_from_pdf(file_path)
            elif file_format in ["jpg", "png"]:
                images = self._load_direct_image(file_path, file_format)
            else:
                self.logger.warning(f"Unsupported format for image forensics: {file_format}")
                images = []
            
            images_analyzed = len(images)
            
            if images_analyzed == 0:
                self.logger.info("   No images found in document")
                state["images_analyzed"] = 0
                state["image_forensics_executed"] = True
                state["image_forensics_score"] = 100
                return state

            self.logger.info(f"   Found {images_analyzed} image(s)")

            # Step 2: Analyze each image
            for idx, image_data in enumerate(images[:10]):  # Limit to 10 images
                self.logger.info(f"\n📸 Analyzing Image {idx + 1}/{min(images_analyzed, 10)}")
                
                image_result = await self._analyze_single_image(
                    image_data,
                    idx,
                    document_id
                )
                
                if image_result:
                    image_findings.append(image_result)
                    
                    # Aggregate findings
                    if image_result.get("ai_generated_likely"):
                        ai_generated_detected = True
                        ai_detection_confidence = max(
                            ai_detection_confidence,
                            image_result.get("ai_confidence", 0)
                        )
                    
                    if image_result.get("tampering_detected"):
                        image_tampering_detected = True
                    
                    exif_issues.extend(image_result.get("exif_issues", []))
                    
                    if image_result.get("reverse_search_match"):
                        reverse_search_results.append(image_result["reverse_search_match"])

            # Step 3: Calculate overall image forensics score
            image_forensics_score = self._calculate_forensics_score(
                image_findings,
                ai_generated_detected,
                image_tampering_detected,
                len(exif_issues)
            )

            self.logger.info(
                f"\nImage forensics completed: {images_analyzed} images, "
                f"AI-gen={ai_generated_detected}, tampering={image_tampering_detected}, "
                f"score={image_forensics_score}"
            )

        except Exception as e:
            self.logger.error(f"Image forensics error: {e}", exc_info=True)
            errors.append(f"Image forensics error: {str(e)}")
            image_forensics_score = 70  # Neutral score on error

        # Update state
        state["image_forensics_executed"] = True
        state["images_analyzed"] = images_analyzed
        state["ai_generated_detected"] = ai_generated_detected
        state["ai_detection_confidence"] = ai_detection_confidence
        state["image_tampering_detected"] = image_tampering_detected
        state["exif_issues"] = exif_issues
        state["reverse_search_results"] = reverse_search_results
        state["image_forensics_score"] = image_forensics_score
        state["image_findings"] = image_findings
        state["errors"] = errors

        return state

    def _load_direct_image(self, file_path: str, file_format: str) -> List[Dict[str, Any]]:
        """Load a direct image file (JPG/PNG) for analysis"""
        images = []
        
        try:
            # Read the image file as bytes
            with open(file_path, 'rb') as f:
                image_bytes = f.read()
            
            # Get image dimensions if PIL is available
            width, height = 0, 0
            if self.pil_available:
                from PIL import Image
                img = Image.open(file_path)
                width, height = img.size
                img.close()
            
            images.append({
                "page": 1,  # Images are treated as single page
                "index": 0,
                "xref": None,  # No xref for direct images
                "image_bytes": image_bytes,
                "extension": file_format,
                "width": width,
                "height": height,
                "colorspace": "unknown",
            })
            
            self.logger.info(f"   Loaded {file_format.upper()} image: {width}x{height}")
            
        except Exception as e:
            self.logger.error(f"Error loading image file: {e}")
        
        return images

    def _extract_images_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract all images from PDF document"""
        if not self.fitz_available:
            self.logger.warning("PyMuPDF not available, can't extract images")
            return []

        images = []
        try:
            doc = self.fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        
                        images.append({
                            "page": page_num + 1,
                            "index": img_index,
                            "xref": xref,
                            "image_bytes": base_image["image"],
                            "extension": base_image["ext"],
                            "width": base_image.get("width", 0),
                            "height": base_image.get("height", 0),
                            "colorspace": base_image.get("colorspace", "unknown"),
                        })
                    except Exception as e:
                        self.logger.warning(f"Failed to extract image {img_index} from page {page_num + 1}: {e}")
            
            doc.close()
            
        except Exception as e:
            self.logger.error(f"Error extracting images from PDF: {e}")
        
        return images

    async def _analyze_single_image(
        self,
        image_data: Dict[str, Any],
        index: int,
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze a single image for AI generation and tampering"""
        try:
            image_bytes = image_data["image_bytes"]
            
            result = {
                "image_index": index,
                "page": image_data["page"],
                "width": image_data["width"],
                "height": image_data["height"],
                "format": image_data["extension"],
            }

            # Step 1: Load image with PIL
            if self.pil_available:
                image = self.Image.open(BytesIO(image_bytes))
                result["color_mode"] = image.mode
                result["size_kb"] = len(image_bytes) / 1024

                # Step 2: EXIF Analysis
                exif_data, exif_issues = self._analyze_exif(image_bytes)
                result["exif_data"] = exif_data
                result["exif_issues"] = exif_issues
                
                if exif_issues:
                    self.logger.info(f"   ⚠️  Found {len(exif_issues)} EXIF issue(s)")

                # Step 3: AI Generation Detection
                ai_result = await self._detect_ai_generated(image, image_bytes, image_data)
                result.update(ai_result)
                
                if ai_result.get("ai_generated_likely"):
                    self.logger.warning(
                        f"   🤖 AI-Generated Image Detected! "
                        f"Confidence: {ai_result.get('ai_confidence', 0)}%"
                    )

                # Step 4: Tampering Detection (ELA)
                if self.cv2_available:
                    tampering_result = self._detect_tampering(image_bytes)
                    result.update(tampering_result)
                    
                    if tampering_result.get("tampering_detected"):
                        self.logger.warning("   ✂️  Image Tampering Detected!")

                # Step 5: Reverse Image Search (if enabled and LLM available)
                if self.llm_service:
                    reverse_result = await self._reverse_image_search(image_bytes, image_data)
                    result["reverse_search_match"] = reverse_result

            return result

        except Exception as e:
            self.logger.error(f"Error analyzing image {index}: {e}")
            return None

    def _analyze_exif(self, image_bytes: bytes) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
        """Extract and analyze EXIF metadata"""
        exif_data = {}
        issues = []

        if not self.exif_available:
            return exif_data, issues

        try:
            tags = self.exifread.process_file(BytesIO(image_bytes), details=False)
            
            # Extract key EXIF fields
            important_fields = {
                "Image Make": "camera_make",
                "Image Model": "camera_model",
                "Image Software": "software",
                "Image DateTime": "datetime",
                "EXIF DateTimeOriginal": "datetime_original",
                "EXIF DateTimeDigitized": "datetime_digitized",
                "GPS GPSLatitude": "gps_lat",
                "GPS GPSLongitude": "gps_long",
            }

            for exif_key, result_key in important_fields.items():
                if exif_key in tags:
                    exif_data[result_key] = str(tags[exif_key])

            # Check for suspicious patterns
            software = exif_data.get("software", "").lower()
            
            # AI image generators
            ai_indicators = ["midjourney", "dall-e", "stable diffusion", "dalle", "flux", "leonardo"]
            for indicator in ai_indicators:
                if indicator in software:
                    issues.append({
                        "type": "ai_software",
                        "severity": "critical",
                        "description": f"AI generation software detected in EXIF: {indicator}"
                    })

            # Image editing software
            editing_software = ["photoshop", "gimp", "affinity", "pixlr"]
            for editor in editing_software:
                if editor in software:
                    issues.append({
                        "type": "edited_image",
                        "severity": "medium",
                        "description": f"Image editing software detected: {editor}"
                    })

            # Missing critical metadata
            if not exif_data.get("datetime_original") and not exif_data.get("camera_make"):
                issues.append({
                    "type": "missing_metadata",
                    "severity": "low",
                    "description": "No camera metadata found - may be screenshot or generated"
                })

        except Exception as e:
            self.logger.debug(f"EXIF analysis failed: {e}")
            issues.append({
                "type": "exif_error",
                "severity": "low",
                "description": "Could not read EXIF data"
            })

        return exif_data, issues

    async def _detect_ai_generated(
        self,
        image,
        image_bytes: bytes,
        image_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect if image is AI-generated using heuristics and LLM"""
        result = {
            "ai_generated_likely": False,
            "ai_confidence": 0,
            "ai_indicators": []
        }

        try:
            # Heuristic 1: Image statistics
            stat = self.ImageStat.Stat(image)
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Check for unnatural patterns (AI images often have perfect gradients)
            extrema = stat.extrema
            mean = stat.mean
            stddev = stat.stddev
            
            # Heuristic: AI images often have very smooth color transitions
            if all(s < 30 for s in stddev):
                result["ai_indicators"].append("very_smooth_gradients")
                result["ai_confidence"] += 15

            # Heuristic 2: Perfect symmetry (common in AI)
            width, height = image.size
            if width == height and width % 512 == 0:  # Common AI resolutions
                result["ai_indicators"].append("ai_common_resolution")
                result["ai_confidence"] += 10

            # Heuristic 3: Use LLM for visual analysis (if available)
            if self.llm_service and len(image_bytes) < 1024 * 1024:  # Under 1MB
                llm_result = await self._llm_ai_detection(image_data)
                if llm_result:
                    result["ai_confidence"] += llm_result.get("confidence_boost", 0)
                    result["ai_indicators"].extend(llm_result.get("indicators", []))

            # Determine if AI-generated
            if result["ai_confidence"] >= 50:
                result["ai_generated_likely"] = True

        except Exception as e:
            self.logger.debug(f"AI detection failed: {e}")

        return result

    async def _llm_ai_detection(self, image_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use LLM to analyze image characteristics for AI generation"""
        try:
            prompt = f"""Analyze this image's characteristics for AI generation indicators:

Image Properties:
- Resolution: {image_data['width']}x{image_data['height']}
- Format: {image_data['extension']}
- Colorspace: {image_data['colorspace']}

Check for:
1. Perfect resolution (512x512, 1024x1024, etc.)
2. Unnatural patterns or artifacts
3. AI-typical signatures

Respond in JSON:
{{
    "likely_ai_generated": true/false,
    "confidence_boost": 0-40,
    "indicators": ["list", "of", "findings"],
    "reasoning": "brief explanation"
}}"""

            response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=300
            )

            # Parse JSON
            response_text = response.strip()
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            
            return json.loads(response_text)

        except Exception as e:
            self.logger.debug(f"LLM AI detection failed: {e}")
            return None

    def _detect_tampering(self, image_bytes: bytes) -> Dict[str, Any]:
        """Detect image tampering using advanced pixel-level anomaly detection"""
        result = {
            "tampering_detected": False,
            "tampering_confidence": 0,
            "tampering_indicators": [],
            "pixel_anomalies": []
        }

        if not self.cv2_available:
            return result

        try:
            # Convert bytes to numpy array
            nparr = self.np.frombuffer(image_bytes, self.np.uint8)
            img = self.cv2.imdecode(nparr, self.cv2.IMREAD_COLOR)
            
            if img is None:
                return result

            gray = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2GRAY)
            
            # === PIXEL-LEVEL ANOMALY DETECTION ===
            
            # 1. Laplacian Variance (Edge Consistency)
            laplacian_var = self.cv2.Laplacian(gray, self.cv2.CV_64F).var()
            if laplacian_var > 500:
                result["tampering_indicators"].append("high_edge_variance")
                result["pixel_anomalies"].append({
                    "type": "edge_inconsistency",
                    "value": float(laplacian_var),
                    "threshold": 500
                })
                result["tampering_confidence"] += 20

            # 2. Noise Pattern Analysis
            noise_level = self._analyze_noise_pattern(gray)
            if noise_level.get("inconsistent_noise"):
                result["tampering_indicators"].append("inconsistent_noise_pattern")
                result["pixel_anomalies"].append({
                    "type": "noise_inconsistency",
                    "regions": noise_level.get("suspicious_regions", 0)
                })
                result["tampering_confidence"] += 15

            # 3. JPEG Compression Artifacts (Double JPEG Detection)
            compression_analysis = self._detect_double_jpeg(img, gray)
            if compression_analysis.get("double_compression"):
                result["tampering_indicators"].append("double_jpeg_compression")
                result["pixel_anomalies"].append({
                    "type": "compression_artifact",
                    "evidence": compression_analysis.get("evidence")
                })
                result["tampering_confidence"] += 25

            # 4. Copy-Move Detection (Cloning)
            clone_detection = self._detect_copy_move(gray)
            if clone_detection.get("cloning_detected"):
                result["tampering_indicators"].append("copy_move_forgery")
                result["pixel_anomalies"].append({
                    "type": "cloned_regions",
                    "similarity": clone_detection.get("similarity", 0)
                })
                result["tampering_confidence"] += 30

            # 5. Histogram Analysis (Uniformity Check)
            hist = self.cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist_std = hist.std()
            if hist_std < 50:  # Very uniform histogram
                result["tampering_indicators"].append("uniform_histogram")
                result["pixel_anomalies"].append({
                    "type": "histogram_uniformity",
                    "std_dev": float(hist_std)
                })
                result["tampering_confidence"] += 15

            # 6. Lighting Inconsistency Analysis
            lighting_check = self._analyze_lighting_consistency(img)
            if lighting_check.get("inconsistent_lighting"):
                result["tampering_indicators"].append("lighting_inconsistency")
                result["pixel_anomalies"].append({
                    "type": "lighting_mismatch",
                    "regions": lighting_check.get("suspicious_regions")
                })
                result["tampering_confidence"] += 20

            # 7. Block Artifact Detection (8x8 JPEG blocks)
            block_artifacts = self._detect_block_artifacts(gray)
            if block_artifacts.get("suspicious_blocks"):
                result["tampering_indicators"].append("block_artifacts")
                result["pixel_anomalies"].append({
                    "type": "block_discontinuity",
                    "count": block_artifacts.get("suspicious_blocks")
                })
                result["tampering_confidence"] += 10

            # Final determination
            if result["tampering_confidence"] >= 30:
                result["tampering_detected"] = True

        except Exception as e:
            self.logger.debug(f"Tampering detection failed: {e}")

        return result

    def _analyze_noise_pattern(self, gray_img) -> Dict[str, Any]:
        """Analyze noise patterns for inconsistencies"""
        try:
            # Divide image into blocks and analyze noise in each
            h, w = gray_img.shape
            block_size = 64
            noise_levels = []
            
            for y in range(0, h - block_size, block_size):
                for x in range(0, w - block_size, block_size):
                    block = gray_img[y:y+block_size, x:x+block_size]
                    # Calculate noise using high-pass filter
                    noise = self.cv2.Laplacian(block, self.cv2.CV_64F).var()
                    noise_levels.append(noise)
            
            if len(noise_levels) > 0:
                noise_std = self.np.std(noise_levels)
                noise_mean = self.np.mean(noise_levels)
                
                # Inconsistent noise if std is too high
                if noise_std > noise_mean * 0.5:
                    return {
                        "inconsistent_noise": True,
                        "suspicious_regions": int(sum(1 for n in noise_levels if abs(n - noise_mean) > 2 * noise_std))
                    }
        except Exception as e:
            self.logger.debug(f"Noise analysis failed: {e}")
        
        return {"inconsistent_noise": False}

    def _detect_double_jpeg(self, img, gray_img) -> Dict[str, Any]:
        """Detect double JPEG compression (sign of editing)"""
        try:
            # Calculate DCT coefficients
            dct = self.cv2.dct(self.np.float32(gray_img) / 255.0)
            
            # Check for JPEG grid artifacts (8x8 blocks)
            # Double compression shows periodic patterns
            dct_abs = self.np.abs(dct)
            
            # Look for 8x8 block boundaries
            h, w = dct_abs.shape
            block_edges = []
            
            for i in range(8, h, 8):
                edge_strength = self.np.mean(dct_abs[i-1:i+1, :])
                block_edges.append(edge_strength)
            
            if len(block_edges) > 0:
                edge_variance = self.np.var(block_edges)
                # High variance indicates inconsistent compression
                if edge_variance > 0.1:
                    return {
                        "double_compression": True,
                        "evidence": f"edge_variance={edge_variance:.4f}"
                    }
        except Exception as e:
            self.logger.debug(f"Double JPEG detection failed: {e}")
        
        return {"double_compression": False}

    def _detect_copy_move(self, gray_img) -> Dict[str, Any]:
        """Detect copy-move forgery (cloned regions)"""
        try:
            # Use feature matching to find similar regions
            # Downsample for performance
            small = self.cv2.resize(gray_img, (0, 0), fx=0.5, fy=0.5)
            
            # Create feature detector (ORB is fast and free)
            orb = self.cv2.ORB_create(nfeatures=1000)
            kp, des = orb.detectAndCompute(small, None)
            
            if des is None or len(des) < 10:
                return {"cloning_detected": False}
            
            # Match features against themselves
            bf = self.cv2.BFMatcher(self.cv2.NORM_HAMMING, crossCheck=False)
            matches = bf.knnMatch(des, des, k=3)
            
            # Find suspiciously similar features (excluding self-matches)
            similar_regions = 0
            for match_list in matches:
                if len(match_list) >= 2:
                    # Skip the self-match (distance=0)
                    if match_list[1].distance < 30:  # Very similar
                        similar_regions += 1
            
            # If many regions are similar, likely cloning
            if similar_regions > len(kp) * 0.1:  # >10% similar
                return {
                    "cloning_detected": True,
                    "similarity": int((similar_regions / len(kp)) * 100)
                }
        except Exception as e:
            self.logger.debug(f"Copy-move detection failed: {e}")
        
        return {"cloning_detected": False}

    def _analyze_lighting_consistency(self, img) -> Dict[str, Any]:
        """Analyze lighting consistency across image regions"""
        try:
            # Convert to HSV for better lighting analysis
            hsv = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2]  # Value channel (brightness)
            
            # Divide into quadrants and check brightness consistency
            h, w = v_channel.shape
            mid_h, mid_w = h // 2, w // 2
            
            quadrants = [
                v_channel[:mid_h, :mid_w],      # Top-left
                v_channel[:mid_h, mid_w:],      # Top-right
                v_channel[mid_h:, :mid_w],      # Bottom-left
                v_channel[mid_h:, mid_w:]       # Bottom-right
            ]
            
            brightness_means = [self.np.mean(q) for q in quadrants]
            brightness_std = self.np.std(brightness_means)
            
            # High variance suggests inconsistent lighting
            if brightness_std > 40:
                return {
                    "inconsistent_lighting": True,
                    "suspicious_regions": [i for i, b in enumerate(brightness_means) 
                                         if abs(b - self.np.mean(brightness_means)) > brightness_std]
                }
        except Exception as e:
            self.logger.debug(f"Lighting analysis failed: {e}")
        
        return {"inconsistent_lighting": False}

    def _detect_block_artifacts(self, gray_img) -> Dict[str, Any]:
        """Detect suspicious 8x8 block artifacts (JPEG editing traces)"""
        try:
            h, w = gray_img.shape
            suspicious_blocks = 0
            
            # Check 8x8 block boundaries for discontinuities
            for y in range(0, h - 8, 8):
                for x in range(0, w - 8, 8):
                    # Get block and its neighbors
                    block = gray_img[y:y+8, x:x+8]
                    
                    # Check edge discontinuity
                    if x + 16 < w:
                        right_block = gray_img[y:y+8, x+8:x+16]
                        edge_diff = abs(int(self.np.mean(block[:, -1])) - 
                                      int(self.np.mean(right_block[:, 0])))
                        if edge_diff > 30:  # Suspicious discontinuity
                            suspicious_blocks += 1
            
            if suspicious_blocks > (h // 8) * (w // 8) * 0.05:  # >5% suspicious
                return {"suspicious_blocks": suspicious_blocks}
        except Exception as e:
            self.logger.debug(f"Block artifact detection failed: {e}")
        
        return {"suspicious_blocks": 0}

    async def _reverse_image_search(
        self,
        image_bytes: bytes,
        image_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Perform reverse image search (simulated with LLM analysis)"""
        # Note: Real reverse image search would use Google Vision API, TinEye, etc.
        # This is a simulated version using image hash matching
        
        try:
            # Calculate perceptual hash
            if self.pil_available:
                image = self.Image.open(BytesIO(image_bytes))
                # Simple average hash
                image_small = image.resize((8, 8), self.Image.Resampling.LANCZOS).convert('L')
                pixels = list(image_small.getdata())
                avg = sum(pixels) / len(pixels)
                bits = ''.join('1' if p > avg else '0' for p in pixels)
                image_hash = hex(int(bits, 2))[2:]

                # In production, would search database or external APIs
                # For now, just return hash info
                return {
                    "search_performed": True,
                    "image_hash": image_hash,
                    "matches_found": 0,
                    "note": "Reverse search ready (requires API integration)"
                }

        except Exception as e:
            self.logger.debug(f"Reverse image search failed: {e}")

        return None

    def _calculate_forensics_score(
        self,
        image_findings: List[Dict[str, Any]],
        ai_generated: bool,
        tampering: bool,
        exif_issue_count: int
    ) -> int:
        """Calculate overall image forensics score"""
        score = 100

        # Deduct for AI-generated images
        if ai_generated:
            max_confidence = max(
                (f.get("ai_confidence", 0) for f in image_findings),
                default=0
            )
            score -= min(40, max_confidence // 2)

        # Deduct for tampering
        if tampering:
            score -= 30

        # Deduct for EXIF issues
        score -= min(20, exif_issue_count * 5)

        return max(0, min(100, score))
