from django.apps import AppConfig
import os


class GymAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gym_management.gym_app'
    scheduler_started = False
    
    def ready(self):
        if not GymAppConfig.scheduler_started:
            from apscheduler.schedulers.background import BackgroundScheduler
            from django_apscheduler.jobstores import DjangoJobStore
            from django.conf import settings
            
            scheduler = BackgroundScheduler()
            scheduler.add_jobstore(DjangoJobStore(), "default")
            
            # Import locally to avoid AppRegistryNotReady error
            from gym_management.gym_app.management.commands.check_membership_expiration import check_and_notify_expiring_memberships
            
            scheduler.add_job(
                check_and_notify_expiring_memberships,
                'interval',
                hours=24,
                id='check_membership_expiration',
                replace_existing=True
            )
            
            try:
                scheduler.start()
                GymAppConfig.scheduler_started = True
                print("APScheduler started successfully - checking memberships every 24 hours")
            except Exception as e:
                print(f"Error starting APScheduler: {str(e)}")
                print(f"Failed to start APScheduler: {e}")
