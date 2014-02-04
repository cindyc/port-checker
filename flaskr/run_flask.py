from flask import request, Flask, Response, render_template
from portscanner import PortScanner

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/scan/<ip_addr>", methods=['GET', 'POST'])
def scan_ports(ip_addr):
    if request.method == 'GET':
        data = request.args
        print 'request.args={}'.format(request.args)
    else:
        data = request.form
        print 'request.form={}'.format(request.form)
    scanner = PortScanner(
                          ip_addr,
                          data['username'],
                          data['password']
                         )
    scan_result_json = scanner.scan()
    resp = Response(response=scan_result_json,
                    status=200,
                    mimetype="application/json")

    return resp

if __name__ == "__main__":
    app.run(debug=True)
