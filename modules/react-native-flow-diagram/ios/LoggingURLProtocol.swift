import Foundation

class LoggingURLProtocol: URLProtocol {
    static let handledKey = "LoggingURLProtocolHandledKey"
    private var sessionDataTask: URLSessionDataTask?
    private var startTime: Date?
    private var urlString: String?

    override class func canInit(with request: URLRequest) -> Bool {
        // Prevent infinite recursion
        if URLProtocol.property(forKey: handledKey, in: request) != nil {
            return false
        }

        guard let url = request.url else { return false }
        let urlString = url.absoluteString

        // Filter out URLs we don't want to handle
        if urlString.contains("autoproxy") || urlString.contains("localhost") {
            return false
        }

        // Intercept HTTP and HTTPS requests
        let shouldHandle = url.scheme == "http" || url.scheme == "https"
        return shouldHandle
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        return request
    }

    override func startLoading() {
        guard let url = request.url else {
            client?.urlProtocol(self, didFailWithError: URLError(.badURL))
            return
        }
        urlString = url.absoluteString

        // Log the network request
        FlowDiagramUtil.logNetwork(urlString!, logType: .NE_REQUEST)
        startTime = Date()

        // Mark as handled to avoid recursion
        let newRequest = ((request as NSURLRequest).mutableCopy() as! NSMutableURLRequest)
        URLProtocol.setProperty(true, forKey: LoggingURLProtocol.handledKey, in: newRequest)

        let config = URLSessionConfiguration.default
        let session = URLSession(configuration: config, delegate: nil, delegateQueue: nil)
        sessionDataTask = session.dataTask(with: newRequest as URLRequest) { data, response, error in
            // Calculate elapsed time
            let elapsedTime: Int64
            if let start = self.startTime {
                elapsedTime = Int64(Date().timeIntervalSince(start) * 1000)
            } else {
                elapsedTime = 0
            }
            // Status code
            var statusCode = 0
            if let httpResponse = response as? HTTPURLResponse {
                statusCode = httpResponse.statusCode
            }
            // Log the network response
            FlowDiagramUtil.logNetwork(self.urlString ?? "", logType: .NE_RESPONSE, responseCode: Int32(statusCode), elapsedTime: elapsedTime)

            // Forward data to the client
            if let response = response {
                self.client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            }
            if let data = data {
                self.client?.urlProtocol(self, didLoad: data)
            }
            if let error = error {
                self.client?.urlProtocol(self, didFailWithError: error)
            } else {
                self.client?.urlProtocolDidFinishLoading(self)
            }
        }
        sessionDataTask?.resume()
    }

    override func stopLoading() {
        sessionDataTask?.cancel()
        sessionDataTask = nil
    }
}
