# JN 2015-02-13 refactoring
from __future__ import absolute_import, print_function, division

from collections import defaultdict
from multiprocessing import Process, Queue, Value
from .. import DefaultFilter
from .tools import ExtractNcsFile, OutFile, read_matfile
from .extract_spikes import extract_spikes


def save(q, ctarget):

    openfiles = {}
    saved = 0
    pending_jobs = defaultdict(dict)
    last_saved_count = defaultdict(lambda : -1)
    all_data = []

    while saved < ctarget:
        inp = q.get()

        job = inp[0]
        datatuple = inp[1]
        ind = len(all_data)

        all_data.append(datatuple)
        job.update(all_data_ind=ind)

        jname = job['name']
        this_name_pending_jobs = pending_jobs[jname]

        jcount = job['count']
        this_name_pending_jobs[jcount] = job


        print('Job name: {} pending jobs: {} jnow: {}'.format(jname,
                                                              this_name_pending_jobs.keys(),
                                                              jcount))

        while last_saved_count[jname] + 1 in this_name_pending_jobs:
            sjob = this_name_pending_jobs[last_saved_count[jname] + 1]
            data = all_data[sjob['all_data_ind']]
            if not sjob['name'] in openfiles:

                 spoints = data[0][0].shape[1]
                 openfiles[sjob['name']] = OutFile(sjob['name'], sjob['filename'],
                                                   spoints, sjob['destination'])

            print('saving {}, count {}'.format(sjob['name'], sjob['count']))
            openfiles[sjob['name']].write(data)
            all_data[sjob['all_data_ind']] = None
            last_saved_count[jname] = sjob['count']
            del this_name_pending_jobs[sjob['count']]
            saved += 1


    for fid in openfiles.values():
        fid.close()

    print('Save exited')


def work(q_in, q_out, count, target):

    filters = {}

    while count.value < target:
        with count.get_lock():
            count.value += 1

        inp = q_in.get()
        job = inp[0]
        datatuple = inp[1]

        ts = datatuple[2]

        if not ts in filters:
            filters[ts] = DefaultFilter(ts)

        filt = filters[ts]

        result = extract_spikes(datatuple[0],
                                datatuple[1],
                                ts,  filt)

        q_out.put((job, result))

    print('Work exited')


def read(jobs, q):
    """
    writes to q; q is read by worker processes
    """
    openfiles = {}

    for job in jobs:
        jname = job['name']

        if 'is_matfile' in job.keys():
            if job['is_matfile']:
                fname = job['filename']
                print('Reading from matfile ' + fname)
                data = read_matfile(fname)
                if job['scale_factor'] != 1:
                    print('Rescaling matfile data by {:.4f}'.
                        format(job['scale_factor']))
                    data = (data[0] * job['scale_factor'],
                            data[1],
                            data[2])
                job.update(filename='data_' + jname + '.h5')

        else:
            if jname not in openfiles:
                openfiles[jname] = ExtractNcsFile(job['filename'], job['reference'])

            print('Read {} {: 7d} {: 7d}'.format(jname, job['start'], job['stop']))
            data = openfiles[jname].read(job['start'], job['stop'])
            job.update(filename='data_' + jname + '.h5')

        q.put((job, data))

    print('Read exited')


def mp_extract(jobs, nWorkers):

    procs = []

    ctarget = len(jobs)
    count = Value('i', 0)

    q_read = Queue(5)
    q_work = Queue()

    # start the reading process
    p = Process(target=read, args=[jobs, q_read])
    p.daemon = True
    p.start()

    # start the worker processes
    for i in range(nWorkers):
        p = Process(target=work, args=[q_read, q_work, count, ctarget])
        p.daemon = True
        p.start()
        procs.append(p)

    # start the saver process
    p = Process(target=save, args=[q_work, ctarget])
    p.daemon = True
    p.start()
    p.join()

    for p in procs:
        p.join()
