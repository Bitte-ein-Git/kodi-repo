# -*- coding: utf-8 -*-

from .common import *


def _header(REFERRER=None, XINFOS=None, USERTOKEN=None):
	header = {}
	header['Accept'] = '*/*'
	header['Content-Type'] = 'application/json; charset=utf-8'
	header['User-Agent'] = agent_WEB
	header['DNT'] = '1'
	header['Upgrade-Insecure-Requests'] = '1'
	header['Accept-Encoding'] = 'gzip'
	header['Accept-Language'] = 'de-DE,de;q=0.9,en;q=0.8'
	header['sec-ch-ua-platform'] = 'Windows'
	header['Origin'] = BASE_URL[:-1]
	if XINFOS: # TOKEN // SHOWS // VIDEOS // PLAYBACK
		header['X-Device-Info'] = 'STONEJS/1 (Unknown/Unknown; Windows/NT 10.0; Unknown)'
		header['X-disco-client'] = 'WEB:UNKNOWN:wbdatv:2.1.9'
		header['X-disco-params'] = f"realm={DISCO_REALM}"
		if USERTOKEN: # SHOWS // VIDEOS // PLAYBACK
			header['Authorization'] = f"Bearer {USERTOKEN}"
	if REFERRER: header['Referer'] = REFERRER # AURORA // TOKEN // SHOWS // VIDEOS // PLAYBACK
	return header

class Transmission(object):

	def __init__(self):
		self.maxi_tokentime = 595 # max. Token-Time (Seconds) before clear the Token and delete Token-File [595 = 10 Minutes]
		self.tempSTORE_folder = tempSTORE
		self.tempDISCO_file = storeSECRET

	def convert_epoch(self, epoch):
		CIPHER = datetime(1970,1,1) + timedelta(seconds=int(epoch))
		return CIPHER.strftime('%d.%m.%Y - %H:%M:%S')

	def check_authtoken(self):
		CODING, forceRenew, AUTH_TOKEN = False, False, None
		SELECT_PATH, SECURITY, self.TIME_UTC = self.tempSTORE_folder, self.tempDISCO_file, time.time()
		if SECURITY is not None and os.path.isfile(SECURITY):
			try:
				self.TOKEN_UTC = (os.path.getmtime(SECURITY) + self.maxi_tokentime)
				debug_MS(f"(utilities.check_authtoken) ### SESSION-Time (utc NOW) = {self.convert_epoch(self.TIME_UTC)} || VALID until (utc SESSION) = {self.convert_epoch(self.TOKEN_UTC)} ###")
				if self.TIME_UTC < self.TOKEN_UTC:
					AUTH_TOKEN = preserve(SECURITY)['data']['attributes']['token']
					debug_MS("(utilities.check_authtoken) ### NOTHING CHANGED - TOKENFILE IS OKAY ###")
				else:
					debug_MS("(utilities.check_authtoken) ### TIMEOUT FOR TOKEN - DELETE TOKENFILE ###")
					forceRenew = True
			except:
				failing("(utilities.check_authtoken) XXXXX !!! ERROR = TOKENFILE [TOKENFORMAT IS INVALID] = ERROR !!! XXXXX")
				forceRenew = True
		else:
			debug_MS("(utilities.check_authtoken) ### NOTHING FOUND - CREATE TOKENFILE FOR DISCOVERY ###")
			forceRenew = True
		if forceRenew:
			if SECURITY is not None and os.path.isfile(SECURITY):
				shutil.rmtree(SELECT_PATH, ignore_errors=True)
			CODING = self.retrieveContent(ACCESS_URL, forcing=False)
			if CODING:
				debug_MS(f"(utilities.check_authtoken) ***** NEW TOKENFILE CREATED : {CODING} *****")
				if not xbmcvfs.exists(SELECT_PATH) and not os.path.isdir(SELECT_PATH):
					xbmcvfs.mkdirs(SELECT_PATH)
				preserve(SECURITY, CODING)
				AUTH_TOKEN = CODING['data']['attributes']['token']
		return AUTH_TOKEN

	def retrieveMultiData(self, MURLS, method='GET', REF=BASE_URL, PRO=True, timeout=5, retries=2):
		COMBI_NEW, number = [], len(MURLS)
		def download(pos, url, token):
			CAPTION = _header(REF, None, None) if url.startswith(PUBLIC_HOST) else _header(REF, PRO, token)
			STARTING = f"{EUAPI_SHOWS}&sort=name&filter[primaryChannel.id]={DISCO_CHANNEL}&page[number]=1&page[size]=50"
			UNCHECK = ssl.create_default_context()
			UNCHECK.check_hostname = False
			UNCHECK.verify_mode = ssl.CERT_NONE
			connector = urllib3.PoolManager(block=True, ssl_context=UNCHECK, maxsize=15)
			with connector.request(method, STARTING, headers=_header(REF, PRO, token), preload_content=False, redirect=True, timeout=timeout, retries=retries) as mrs:
				if mrs.status in [200, 201, 202, 300, 301, 302]:
					response = connector.request(method, url, headers=CAPTION, redirect=True, timeout=timeout, retries=retries)
					if response.status in [200, 201, 202, 300, 301, 302]:
						debug_MS(f"(utilities.retrieveMultiData[1]) === POS : {pos} === URL : {url} === HEADER : {CAPTION} ===")
						return f'{{"Position":{pos},"Demand":"{url}",{py3_dec(response.data[1:-1])}}}'
					else:
						failing(f"(utilities.retrieveMultiData[1]) ERROR - RESPONSE - ERROR ##### POS : {pos} === STATUS : {response.status} === URL : {url} #####")
						return '{"ERROR_occurred":true}'
			connector.clear()
		with ThreadPoolExecutor() as executor:
			debug_MS("---------------------------------------------")
			REALCODE = self.check_authtoken()
			picker = [executor.submit(download, pos, url, REALCODE) for pos, url in MURLS]
			wait(picker, timeout=30, return_when=ALL_COMPLETED)
			for ii, future in enumerate(as_completed(picker), 1):
				try:
					COMBI_NEW.append(json.loads(future.result()))
				except Exception as exc:
					failing(f"(utilities.retrieveMultiData[2]) ERROR - EXEPTION - ERROR ##### FUTURE_CONNECT : {future.result()} === FAILURE : {exc} #####")
					dialog.notification(translation(30521).format('DETAILS', ''), translation(30523).format(exc), icon, 12000)
					executor.shutdown()
			if COMBI_NEW:
				matching = [flop for flop in COMBI_NEW[:] if flop.get('ERROR_occurred', '') is True]
				if len(matching) == number or len(matching) > 3:
					dialog.notification(translation(30521).format('DETAILS', ''), translation(30524), icon, 12000)
			return json.dumps(COMBI_NEW, indent=2)

	def retrieveContent(self, url, method='GET', queries='JSON', REF=BASE_URL, PRO=True, forcing=True, headers={}, redirects=True, verify=False, data=None, json=None, timeout=30):
		attempts, ANSWER = 0, None
		ACTUCODE = self.check_authtoken() if forcing is True else None
		SPECIFICS = _header(REF, None, None) if url.startswith(PUBLIC_HOST) else _header(REF, PRO, ACTUCODE)
		while not ANSWER and attempts < 2: # 2 x Pingversuche für den Request ::: zur Überprüfung der Verfügbarkeit der URL
			attempts += 1
			try:
				response = requests.request(method, url, headers=SPECIFICS, allow_redirects=redirects, verify=verify, data=data, json=json, timeout=timeout)
				ANSWER = response.json() if queries == 'JSON' else response.text if queries == 'TEXT' else response
				debug_MS(f"(utilities.retrieveContent) === CALLBACK === STATUS : {response.status_code} || URL : {response.url} || HEADER : {SPECIFICS} || DATA : {data} ===")
				if queries == 'JSON' and not isinstance(response.json(), list) and response.json().get('errors', ''):
					message = (response.json().get('errors', {})[0].get('detail', '') or 'NO DETAILS FOUND')
					failing(f"(utilities.retrieveContent) ERROR - RESPONSE - ERROR ##### URL : {url} === DETAIL : {message} #####")
					dialog.notification(translation(30521).format('URL', ''), translation(30523).format(message), icon, 12000)
					return sys.exit(0)
				response.raise_for_status()
			except Exception as exc: # No JSON object could be decoded
				failing(f"(utilities.retrieveContent) ERROR - EXEPTION - ERROR ##### URL : {url} === FAILURE : {exc} #####")
				dialog.notification(translation(30521).format('URL', ''), translation(30523).format(exc), icon, 12000)
				time.sleep(2)
				if attempts >= 2: return sys.exit(0)
		return ANSWER
