"""Cost Explorer service for cost analysis."""

from datetime import datetime, timedelta
from typing import Any, Optional
import statistics

from app.services.aws.base import AWSBaseService
from app.models.schemas import (
    CostSummaryResponse,
    CostBreakdownResponse,
    CostByService,
    CostByRegion,
    CostForecastResponse,
    CostRecommendationsResponse,
    CostRecommendation,
)


class CostExplorerService(AWSBaseService):
    """Service for Cost Explorer operations."""

    async def get_cost_summary(self) -> CostSummaryResponse:
        """Get cost summary including MTD, last month, and YTD."""
        now = datetime.utcnow()

        # MTD
        mtd_start = now.replace(day=1)
        mtd_cost = await self._get_cost_for_period(mtd_start, now)

        # Last month
        last_month_end = mtd_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        last_month_cost = await self._get_cost_for_period(
            last_month_start, last_month_end
        )

        # YTD
        ytd_start = now.replace(month=1, day=1)
        ytd_cost = await self._get_cost_for_period(ytd_start, now)

        # Forecast
        forecast = await self.get_cost_forecast()

        return CostSummaryResponse(
            mtd_cost=mtd_cost,
            mtd_forecast=forecast.forecasted_cost,
            last_month_cost=last_month_cost,
            ytd_cost=ytd_cost,
            period_start=mtd_start,
            period_end=now,
        )

    async def _get_cost_for_period(
        self,
        start: datetime,
        end: datetime,
    ) -> float:
        """Get total cost for a date range."""
        async with await self.get_client("ce") as ce:
            response = await ce.get_cost_and_usage(
                TimePeriod={
                    "Start": start.strftime("%Y-%m-%d"),
                    "End": end.strftime("%Y-%m-%d"),
                },
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )

            total = 0.0
            for result in response.get("ResultsByTime", []):
                amount = result.get("Total", {}).get("UnblendedCost", {}).get("Amount", "0")
                total += float(amount)

            return round(total, 2)

    async def get_cost_breakdown(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "MONTHLY",
    ) -> CostBreakdownResponse:
        """Get cost breakdown by service and region."""
        now = datetime.utcnow()
        if not start_date:
            start_date = now.replace(day=1)
        if not end_date:
            end_date = now

        async with await self.get_client("ce") as ce:
            # By service
            service_response = await ce.get_cost_and_usage(
                TimePeriod={
                    "Start": start_date.strftime("%Y-%m-%d"),
                    "End": end_date.strftime("%Y-%m-%d"),
                },
                Granularity=granularity,
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )

            # By region
            region_response = await ce.get_cost_and_usage(
                TimePeriod={
                    "Start": start_date.strftime("%Y-%m-%d"),
                    "End": end_date.strftime("%Y-%m-%d"),
                },
                Granularity=granularity,
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "REGION"}],
            )

        # Process service costs
        service_costs = {}
        for result in service_response.get("ResultsByTime", []):
            for group in result.get("Groups", []):
                service = group["Keys"][0]
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                service_costs[service] = service_costs.get(service, 0) + amount

        # Process region costs
        region_costs = {}
        for result in region_response.get("ResultsByTime", []):
            for group in result.get("Groups", []):
                region = group["Keys"][0]
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                region_costs[region] = region_costs.get(region, 0) + amount

        total = sum(service_costs.values())

        by_service = [
            CostByService(
                service=service,
                cost=round(cost, 2),
                percentage=round((cost / total) * 100, 1) if total > 0 else 0,
            )
            for service, cost in sorted(
                service_costs.items(), key=lambda x: x[1], reverse=True
            )
        ]

        by_region = [
            CostByRegion(
                region=region,
                cost=round(cost, 2),
                percentage=round((cost / total) * 100, 1) if total > 0 else 0,
            )
            for region, cost in sorted(
                region_costs.items(), key=lambda x: x[1], reverse=True
            )
        ]

        return CostBreakdownResponse(
            by_service=by_service,
            by_region=by_region,
            total=round(total, 2),
            period_start=start_date,
            period_end=end_date,
        )

    async def get_cost_forecast(self) -> CostForecastResponse:
        """Get forecasted costs for current month."""
        now = datetime.utcnow()
        month_end = (now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        async with await self.get_client("ce") as ce:
            try:
                response = await ce.get_cost_forecast(
                    TimePeriod={
                        "Start": now.strftime("%Y-%m-%d"),
                        "End": month_end.strftime("%Y-%m-%d"),
                    },
                    Metric="UNBLENDED_COST",
                    Granularity="MONTHLY",
                )

                return CostForecastResponse(
                    forecasted_cost=round(float(response["Total"]["Amount"]), 2),
                    confidence_level=0.8,  # Default confidence
                    period_start=now,
                    period_end=month_end,
                )
            except Exception:
                # Forecast might fail if not enough historical data
                return CostForecastResponse(
                    forecasted_cost=0.0,
                    confidence_level=0.0,
                    period_start=now,
                    period_end=month_end,
                )

    async def get_daily_costs(self, days: int = 30) -> list[dict[str, Any]]:
        """Get daily costs for the last N days."""
        now = datetime.utcnow()
        start = now - timedelta(days=days)

        async with await self.get_client("ce") as ce:
            response = await ce.get_cost_and_usage(
                TimePeriod={
                    "Start": start.strftime("%Y-%m-%d"),
                    "End": now.strftime("%Y-%m-%d"),
                },
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
            )

        daily_costs = []
        for result in response.get("ResultsByTime", []):
            daily_costs.append({
                "date": result["TimePeriod"]["Start"],
                "cost": round(
                    float(result["Total"]["UnblendedCost"]["Amount"]), 2
                ),
            })

        return daily_costs

    async def get_costs_by_tag(
        self,
        tag_key: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Get costs grouped by tag value."""
        now = datetime.utcnow()
        if not start_date:
            start_date = now.replace(day=1)
        if not end_date:
            end_date = now

        async with await self.get_client("ce") as ce:
            response = await ce.get_cost_and_usage(
                TimePeriod={
                    "Start": start_date.strftime("%Y-%m-%d"),
                    "End": end_date.strftime("%Y-%m-%d"),
                },
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "TAG", "Key": tag_key}],
            )

        tag_costs = {}
        for result in response.get("ResultsByTime", []):
            for group in result.get("Groups", []):
                tag_value = group["Keys"][0].replace(f"{tag_key}$", "") or "Untagged"
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                tag_costs[tag_value] = tag_costs.get(tag_value, 0) + amount

        return [
            {"tag_value": tag, "cost": round(cost, 2)}
            for tag, cost in sorted(tag_costs.items(), key=lambda x: x[1], reverse=True)
        ]

    async def get_recommendations(self) -> CostRecommendationsResponse:
        """Get cost optimization recommendations."""
        recommendations = []
        total_savings = 0.0

        # Get idle EC2 instances
        idle_ec2 = await self._find_idle_ec2_instances()
        for rec in idle_ec2:
            recommendations.append(rec)
            total_savings += rec.estimated_monthly_savings

        # Get unattached EBS volumes
        unattached_ebs = await self._find_unattached_volumes()
        for rec in unattached_ebs:
            recommendations.append(rec)
            total_savings += rec.estimated_monthly_savings

        # Get old snapshots
        old_snapshots = await self._find_old_snapshots()
        for rec in old_snapshots:
            recommendations.append(rec)
            total_savings += rec.estimated_monthly_savings

        # Get underutilized RDS instances
        underutilized_rds = await self._find_underutilized_rds()
        for rec in underutilized_rds:
            recommendations.append(rec)
            total_savings += rec.estimated_monthly_savings

        # Get unoptimized S3 buckets
        unoptimized_s3 = await self._find_unoptimized_s3_buckets()
        for rec in unoptimized_s3:
            recommendations.append(rec)
            total_savings += rec.estimated_monthly_savings

        # Get unused Lambda functions
        unused_lambda = await self._find_unused_lambda_functions()
        for rec in unused_lambda:
            recommendations.append(rec)
            total_savings += rec.estimated_monthly_savings

        return CostRecommendationsResponse(
            recommendations=recommendations,
            total_potential_savings=round(total_savings, 2),
        )

    async def _find_idle_ec2_instances(self) -> list[CostRecommendation]:
        """Find EC2 instances with low CPU utilization."""
        from app.services.aws.ec2 import EC2Service

        recommendations = []
        ec2_service = EC2Service(region=self.region)
        instances = await ec2_service.list_instances(
            filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )

        for instance in instances[:10]:  # Limit to 10 for performance
            metrics = await ec2_service.get_instance_metrics(
                instance.resource_id,
                metric_name="CPUUtilization",
                hours=168,  # 7 days
            )

            if metrics:
                avg_cpu = statistics.mean([m["average"] for m in metrics if m.get("average")])
                if avg_cpu < 5:  # Less than 5% CPU
                    # Estimate cost based on instance type (simplified)
                    estimated_cost = 50  # Placeholder
                    recommendations.append(
                        CostRecommendation(
                            resource_id=instance.resource_id,
                            resource_type="ec2",
                            recommendation_type="idle_instance",
                            description=f"Instance has {avg_cpu:.1f}% average CPU utilization over 7 days. Consider stopping or downsizing.",
                            estimated_monthly_savings=estimated_cost,
                            current_monthly_cost=estimated_cost,
                            priority="high" if avg_cpu < 2 else "medium",
                        )
                    )

        return recommendations

    async def _find_unattached_volumes(self) -> list[CostRecommendation]:
        """Find unattached EBS volumes."""
        from app.services.aws.ec2 import EC2Service

        recommendations = []
        ec2_service = EC2Service(region=self.region)
        volumes = await ec2_service.list_volumes()

        for volume in volumes:
            if volume.metadata.get("attachment_state") == "unattached":
                size_gb = volume.metadata.get("size_gb", 0)
                # Estimate cost: ~$0.10/GB-month for gp2
                estimated_cost = size_gb * 0.10

                recommendations.append(
                    CostRecommendation(
                        resource_id=volume.resource_id,
                        resource_type="ebs",
                        recommendation_type="unattached_volume",
                        description=f"Volume ({size_gb} GB) is not attached to any instance. Consider deleting or snapshotting.",
                        estimated_monthly_savings=estimated_cost,
                        current_monthly_cost=estimated_cost,
                        priority="medium",
                    )
                )

        return recommendations

    async def _find_old_snapshots(self, days_old: int = 90) -> list[CostRecommendation]:
        """Find old EBS snapshots."""
        from app.services.aws.ec2 import EC2Service
        from datetime import datetime

        recommendations = []
        ec2_service = EC2Service(region=self.region)
        snapshots = await ec2_service.list_snapshots()

        cutoff = datetime.utcnow() - timedelta(days=days_old)

        for snapshot in snapshots:
            start_time_str = snapshot.metadata.get("start_time")
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                if start_time.replace(tzinfo=None) < cutoff:
                    size_gb = snapshot.metadata.get("size_gb", 0)
                    # Snapshot storage: ~$0.05/GB-month
                    estimated_cost = size_gb * 0.05

                    recommendations.append(
                        CostRecommendation(
                            resource_id=snapshot.resource_id,
                            resource_type="ebs_snapshot",
                            recommendation_type="old_snapshot",
                            description=f"Snapshot is over {days_old} days old. Consider deleting if no longer needed.",
                            estimated_monthly_savings=estimated_cost,
                            current_monthly_cost=estimated_cost,
                            priority="low",
                        )
                    )

        return recommendations

    async def _find_underutilized_rds(self) -> list[CostRecommendation]:
        """Find RDS instances with low utilization."""
        from app.services.aws.rds import RDSService

        recommendations = []
        rds_service = RDSService(region=self.region)
        instances = await rds_service.list_instances()

        for instance in instances:
            # Get CloudWatch metrics for CPU
            metrics = await self._get_rds_metrics(
                instance.resource_id,
                metric_name="CPUUtilization",
                hours=168,  # 7 days
            )

            if metrics:
                avg_cpu = statistics.mean([m["average"] for m in metrics if m.get("average") is not None])

                # Check for low utilization (< 20% CPU)
                if avg_cpu < 20:
                    # Estimate monthly cost based on instance class
                    instance_class = instance.metadata.get("instance_class", "")
                    estimated_cost = self._estimate_rds_cost(instance_class)
                    potential_savings = estimated_cost * 0.3  # 30% savings from downsizing

                    priority = "high" if avg_cpu < 5 else "medium" if avg_cpu < 10 else "low"

                    recommendations.append(
                        CostRecommendation(
                            resource_id=instance.resource_id,
                            resource_type="rds",
                            recommendation_type="underutilized_rds",
                            description=f"RDS instance has {avg_cpu:.1f}% average CPU over 7 days. Consider downsizing to a smaller instance class.",
                            estimated_monthly_savings=potential_savings,
                            current_monthly_cost=estimated_cost,
                            priority=priority,
                        )
                    )

        return recommendations

    async def _get_rds_metrics(
        self,
        db_instance_id: str,
        metric_name: str = "CPUUtilization",
        hours: int = 168,
    ) -> list[dict]:
        """Get CloudWatch metrics for an RDS instance."""
        async with await self.get_client("cloudwatch") as cloudwatch:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            response = await cloudwatch.get_metric_statistics(
                Namespace="AWS/RDS",
                MetricName=metric_name,
                Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour
                Statistics=["Average", "Maximum"],
            )

            return [
                {
                    "timestamp": dp["Timestamp"].isoformat(),
                    "average": dp.get("Average"),
                    "maximum": dp.get("Maximum"),
                }
                for dp in response.get("Datapoints", [])
            ]

    def _estimate_rds_cost(self, instance_class: str) -> float:
        """Estimate monthly cost for RDS instance class."""
        # Simplified pricing estimates (us-east-1, MySQL, single-AZ)
        pricing = {
            "db.t3.micro": 12.0,
            "db.t3.small": 24.0,
            "db.t3.medium": 48.0,
            "db.t3.large": 96.0,
            "db.t3.xlarge": 192.0,
            "db.r5.large": 175.0,
            "db.r5.xlarge": 350.0,
            "db.r5.2xlarge": 700.0,
            "db.m5.large": 125.0,
            "db.m5.xlarge": 250.0,
        }
        return pricing.get(instance_class, 100.0)  # Default to $100

    async def _find_unoptimized_s3_buckets(self) -> list[CostRecommendation]:
        """Find S3 buckets that could be optimized."""
        from app.services.aws.s3 import S3Service

        recommendations = []
        s3_service = S3Service(region=self.region)
        buckets = await s3_service.list_buckets()

        for bucket in buckets[:20]:  # Limit to 20 buckets for performance
            bucket_name = bucket.resource_id

            try:
                # Check if bucket has lifecycle policy
                has_lifecycle = await s3_service.has_lifecycle_policy(bucket_name)

                # Get bucket size metrics from CloudWatch
                metrics = await s3_service.get_bucket_metrics(bucket_name)
                size_bytes = metrics.get("size_bytes", 0)
                object_count = metrics.get("object_count", 0)

                # Check for empty buckets (0 objects based on metrics)
                if object_count == 0:
                    recommendations.append(
                        CostRecommendation(
                            resource_id=bucket_name,
                            resource_type="s3",
                            recommendation_type="empty_bucket",
                            description="Bucket appears empty or has no CloudWatch metrics. Consider deleting if no longer needed.",
                            estimated_monthly_savings=0.0,
                            current_monthly_cost=0.0,
                            priority="low",
                        )
                    )
                # Check for buckets without lifecycle policies (if they have significant data)
                elif not has_lifecycle and size_bytes > 1024 * 1024 * 100:  # > 100MB
                    size_gb = size_bytes / (1024 * 1024 * 1024)
                    # Estimate savings from transitioning to IA storage (~40% savings)
                    current_cost = size_gb * 0.023  # S3 Standard pricing
                    potential_savings = current_cost * 0.4

                    recommendations.append(
                        CostRecommendation(
                            resource_id=bucket_name,
                            resource_type="s3",
                            recommendation_type="no_lifecycle_policy",
                            description=f"Bucket has {size_gb:.1f} GB without lifecycle policy. Add lifecycle rules to transition old objects to cheaper storage classes.",
                            estimated_monthly_savings=potential_savings,
                            current_monthly_cost=current_cost,
                            priority="medium",
                        )
                    )
            except Exception:
                # Skip bucket if we can't get its info
                continue

        return recommendations

    async def _find_unused_lambda_functions(self) -> list[CostRecommendation]:
        """Find Lambda functions with no recent invocations."""
        from app.services.aws.lambda_ import LambdaService

        recommendations = []
        lambda_service = LambdaService(region=self.region)
        functions = await lambda_service.list_functions()

        for func in functions:
            function_name = func.resource_id

            # Get invocation metrics for last 30 days
            invocations = await self._get_lambda_invocations(function_name, days=30)

            if invocations == 0:
                # Estimate cost based on code size (storage cost)
                code_size_mb = func.metadata.get("code_size", 0) / (1024 * 1024)
                storage_cost = code_size_mb * 0.0000166667  # $0.10 per GB-month

                recommendations.append(
                    CostRecommendation(
                        resource_id=function_name,
                        resource_type="lambda",
                        recommendation_type="unused_function",
                        description=f"Lambda function has 0 invocations in the last 30 days. Consider deleting if no longer needed.",
                        estimated_monthly_savings=storage_cost,
                        current_monthly_cost=storage_cost,
                        priority="low",
                    )
                )

        return recommendations

    async def _get_lambda_invocations(self, function_name: str, days: int = 30) -> int:
        """Get total invocations for a Lambda function over a period."""
        async with await self.get_client("cloudwatch") as cloudwatch:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            response = await cloudwatch.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Invocations",
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400 * days,  # Entire period
                Statistics=["Sum"],
            )

            datapoints = response.get("Datapoints", [])
            if datapoints:
                return int(sum(dp.get("Sum", 0) for dp in datapoints))
            return 0

    async def detect_anomalies(self, days: int = 30) -> list[dict[str, Any]]:
        """Detect cost anomalies using standard deviation."""
        daily_costs = await self.get_daily_costs(days)

        if len(daily_costs) < 7:
            return []

        costs = [d["cost"] for d in daily_costs]
        mean = statistics.mean(costs)
        stdev = statistics.stdev(costs) if len(costs) > 1 else 0

        threshold = mean + (2 * stdev)
        anomalies = []

        for day_data in daily_costs:
            if day_data["cost"] > threshold:
                anomalies.append({
                    "date": day_data["date"],
                    "cost": day_data["cost"],
                    "expected_max": round(threshold, 2),
                    "deviation": round((day_data["cost"] - mean) / stdev, 2) if stdev > 0 else 0,
                })

        return anomalies
