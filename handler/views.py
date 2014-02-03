import os
import re
import ast
import json
import MySQLdb

# Load Django utilities
from django.http import HttpResponse
from django.core.mail import send_mail
from django.views.generic import View
from django.shortcuts import render

# Load OpenStack utilities
from novaclient.v1_1 import client as nova
from keystoneclient.v2_0 import client as keystone

# TODO:
#
# 1.) Retrieve all arguments passed in the callback URL and convert to dictionary
# 2.) Include keystone/nova API bindings
# 3.) If all parameters supplied, VM creation success
#    1.) Make any updates to the OpenStack DB (IP reservations)
#    2.) Find the email of the user who created the VM
#    3.) Send email to the user with password and IP addresses
# 4.) If an error is passed, VM creation failed
#    1.) Log the error message in the instance metadata
#    2.) Switch the VM to another project (maybe a 'troubleshoot' or 'error' project for broken VMs)
#    3.) Send an email to an internal administrator
#
# FUTURE: Could potentially include a JSON string in the response sent to the VM. The
# cloud init scripts on the VM could then take post-init actions depending on what the
# main OpenStack server determines from database information.

def error_500(request):
    return render(request, '500.html', {}, status=500)

def error_404(request):
    return render(request, '404.html', {}, status=404)

class ResponseHandler(View):
    
    # Initialize the response handler
    def _construct(self):
        
        # Set the Keystone user credentials
        self.os_user = 'admin'
        self.os_pass = 'lamepassword'
        self.os_proj = 'admin'
        self.os_auth = 'http://some.domain:35357/v2.0'
        
        # Set the nova database connection parameters
        self.nova_db_user = 'nova'
        self.nova_db_pass = 'lamepassword'
        self.nova_db_host = 'localhost'
        self.nova_db_name = 'nova'
        
        # Create the nova client connection
        self.nova_client = nova.Client(username = self.os_user,
                                       api_key = self.os_pass,
                                       project_id = self.os_proj,
                                       auth_url = self.os_auth)
        
        # Create the keystone client connection
        self.ks_client   = keystone.Client(username = self.os_user,
                                           password = self.os_pass,
                                           tenant_name = self.os_proj,
                                           auth_url = self.os_auth)
        
        # Create the nova database connection
        self.nova_dbc    = MySQLdb.connect(host = self.nova_db_host,
                                           user = self.nova_db_user,
                                           passwd = self.nova_db_pass,
                                           db = self.nova_db_name)
        self.nova_db     = self.nova_dbc.cursor()
        
    # Process the callback URL parameters
    def get(self, request):
        self._construct()
        
        # Get all the query parameters in the callback URL
        rsp_params = dict(request.GET.iterlists())       
        status     = str(rsp_params['status'][0])
        node       = str(rsp_params['host'][0])
        uuid       = str(rsp_params['uuid'][0])
        passwd     = str(rsp_params['password'][0])
        ip_pub     = str(rsp_params['ip_pub'][0])
        ip_priv    = str(rsp_params['ip_priv'][0])
        
        # If the status is error
        if status == 'error':
            
            # Move the VM to the maintenance project
            #nova_client.servers.lock(uuid)
            exit()
            
        else:
            
            # Get the ID of the instance owner
            self.nova_db.execute("SELECT user_id FROM instances WHERE uuid='" + uuid + "'")
            user_row = self.nova_db.fetchone()
            user_id  = str(user_row[0])
            
            # Get the user email
            user_details = str(self.ks_client.users.get(user_id))
            user_rx      = re.compile(r'<User ({.*})>')
            user_str     = user_rx.sub('\g<1>', user_details)
            user_obj     = ast.literal_eval(user_str)
            user_email   = user_obj['email']
                       
            # Define the email properties
            email_subj   = 'VPLS OpenStack: Your cloud server "' + node + '" is ready!'
            email_msg    = 'Your cloud server "' + node + '" has finished building. You can now log in and start using your \n' \
                           'new cloud server with the information below. Please remember to change the root password.\n\n' \
                           'IP (Public): "' + ip_pub + '"\n' \
                           'IP (Private): "' + ip_priv + '"\n' \
                           'Root Password: "' + passwd + '"'
            email_from   = 'openstack@vpls.net'
            
            # Send the confirmation email              
            send_mail(email_subj, email_msg, email_from, [user_email], fail_silently=False)
            vm_response = {'cb_action': 'none'}
            response = HttpResponse(json.dumps(vm_response), content_type='application/json', status=200)
            return response