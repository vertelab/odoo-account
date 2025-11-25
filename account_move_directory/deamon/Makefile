
# Define the Python file and the systemd service file
PY_FILE = account_move_directory.py
SYSTEMD_SERVICE_FILE = account_move_directory.service
START_SCRIPT = account_move_directory



# Define the installation directories
INSTALL_DIR = /usr/local/bin
SYSTEMD_DIR = /etc/systemd/system

# Define the user and group for the systemd service
USER = odoo
GROUP = odoo

all: install

install: $(PY_FILE)
	# Install the Python file
	cp $(PY_FILE) $(INSTALL_DIR)/$(START_SCRIPT)
	chmod +x $(INSTALL_DIR)/$(START_SCRIPT)

	# Install the systemd service file
	cp $(SYSTEMD_SERVICE_FILE) $(SYSTEMD_DIR)
	chmod 644 $(SYSTEMD_DIR)/$(SYSTEMD_SERVICE_FILE)

	# Reload the systemd daemon
	systemctl daemon-reload

	# Enable and start the systemd service
	systemctl enable $(SYSTEMD_SERVICE_FILE)
	systemctl start $(SYSTEMD_SERVICE_FILE)

uninstall:
	# Stop and disable the systemd service
	systemctl stop $(SYSTEMD_SERVICE_FILE)
	systemctl disable $(SYSTEMD_SERVICE_FILE)

	# Remove the systemd service file
	rm $(SYSTEMD_DIR)/$(SYSTEMD_SERVICE_FILE)

	# Remove the systemd timer file
	-rm $(SYSTEMD_DIR)/$(SYSTEMD_TIMER_FILE)

	# Remove the Python file and the start script
	-rm $(INSTALL_DIR)/$(PY_FILE)
	rm $(INSTALL_DIR)/$(START_SCRIPT)

	# Reload the systemd daemon
	systemctl daemon-reload
