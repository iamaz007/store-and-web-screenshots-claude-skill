// Text-line bounding boxes for an image, via Apple's Vision framework.
//
// The compositor needs to know where the words are before it crops. Without
// this it cuts blind, and a crop line through the middle of a headline is the
// single most obvious sign that a board was generated rather than composed.
//
//   swift textmap.swift shot.png
//   -> one line per text observation: x0 y0 x1 y1 confidence  (0-1, top-left origin)
//
// Vision ships with macOS, so this needs no install - no tesseract, no python
// OCR package, no model download.

import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1 else {
    FileHandle.standardError.write("usage: textmap.swift <image>\n".data(using: .utf8)!)
    exit(2)
}
let path = CommandLine.arguments[1]

guard let image = NSImage(contentsOfFile: path),
      let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("cannot read \(path)\n".data(using: .utf8)!)
    exit(1)
}

let request = VNRecognizeTextRequest()
// `.fast` is the right trade here: the exact glyphs do not matter, only where
// the lines of text sit. Language correction is off for the same reason.
request.recognitionLevel = .fast
request.usesLanguageCorrection = false

let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do {
    try handler.perform([request])
} catch {
    FileHandle.standardError.write("vision failed: \(error)\n".data(using: .utf8)!)
    exit(1)
}

for obs in (request.results ?? []) {
    let b = obs.boundingBox          // normalized, origin bottom-left
    let conf = obs.confidence
    // The recognized string comes last, tab-separated, so callers that only
    // want geometry can ignore it - and callers that need to spot a dead page
    // ("Site not found", "404") can read it.
    let txt = obs.topCandidates(1).first?.string ?? ""
    print("\(b.minX) \(1 - b.maxY) \(b.maxX) \(1 - b.minY) \(conf)\t\(txt)")
}
