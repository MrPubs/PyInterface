
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import yaml
import datetime
from time import sleep

class DBHandler():

    '''
    InfluxDB Handler for main Interface to Read & Write to DB
    Requires Fitting to database using custom Database.yaml config & InfluxQL Queries!
    '''

    def __init__(self,run_no, sess_controller, write_queue):

        '''

        :param run_no: Run number for Logging to the proper run.
        :param sess_controller: Shared Value between Processes of Interface Session.
        :param write_queue: Shared Queue between Processes of the Interface (Reads from Brain) of Writing Data
        '''

        # Parameters
        self.sess = sess_controller
        self.run_no = run_no
        self.write_queue = write_queue # Shared To Write List
        self.writelst = [] # Pending Write List

        # Read & Set Datasheet
        with open('Database.yaml','r') as yamlf:
            self.dbconfig = yaml.safe_load(yamlf)

        self.url = self.dbconfig['url']
        self.token = self.dbconfig['token']
        self.org_id = self.dbconfig['org_id']
        self.bucket_id = self.dbconfig['bucket_id']
        self.bucket_name = self.dbconfig['bucket_name']

        # Clients
        self.dbclient = influxdb_client.InfluxDBClient(url=self.url, token=self.token, org=self.org_id)
        self.wapi = self.dbclient.write_api(write_options=SYNCHRONOUS)
        self.dapi = self.dbclient.delete_api()
        self.qapi = self.dbclient.query_api()

        pass

    def work(self) -> None:

        '''
        Writer work loop.
        :return: None
        '''

        while True:

            # Session Start
            if self.sess.value:

                # self.clear_bucket(bucket_name=self.bucket_name)
                self.get_run_no()
                print(f'[DBHandler] Run #{self.run_no.value+1}!')

                pass
                # Session Loop
                while self.sess.value:
                    # sleep(0.01)

                    # Add To Pending Write List
                    self.writelst.append(self.write_queue.get())
                    if len(self.writelst) >= 250:

                        # Write!
                        self.write(data=self.writelst)
                        self.writelst = []

                # Session End
                pass

    def write(self,data) -> None:
        '''
        Write Data To Bucket
        :param data: Data To Write
        :return: None
        '''
        self.wapi.write(bucket=self.bucket_id, org=self.org_id, record=data)

    def clear_bucket(self, bucket_name: str) -> None:

        '''
        Helper function to wipe bucket. CAREFUL!
        :param bucket_name: Name of bucket to clear
        :return: None
        '''

        # Time Frame
        now = datetime.datetime.utcnow()
        start = (now - datetime.timedelta(weeks=400)).isoformat() + 'Z'
        stop = (now + datetime.timedelta(days=1)).isoformat() + 'Z'

        # Get Msrmnts
        q = f'import "influxdata/influxdb/schema"\n\nschema.measurements(bucket: "{bucket_name}")'
        msrmnts = [list(item)[-1] for item in self.qapi.query(q).to_values()]

        # Delete
        for msrmnt in msrmnts:
            print(f'[DBHandler] Deleting Measurement: {msrmnt} From Bucket: {bucket_name}')
            self.dapi.delete(start, stop, f'_measurement="{msrmnt}"', bucket=self.bucket_id, org=self.org_id)

    def get_run_no(self) -> int:

        '''
        Query DB and get last Run.
        :return: Current Run as integer.
        '''

        # Query for last run
        now = datetime.datetime.utcnow()
        query = f'''
                from(bucket: {None})
                  |> range(start: {(now - datetime.timedelta(weeks=100)).isoformat() + 'Z'}, stop: {now.isoformat() + 'Z'})
                  |> filter(fn: (r) => r[{None}] == {None})
                  |> last()
                '''

        # Take Last Run
        tables = self.qapi.query(query=query)

        if tables:
            runs = []

            for table in tables:

                for record in table.records:
                    runs.append(int(record[{None}]))

            self.run_no.value = max(runs)

        return self.run_no.value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


if __name__ == '__main__':

    with DBHandler(run_no=True,sess_controller=[]) as writer:
        writer.work()
